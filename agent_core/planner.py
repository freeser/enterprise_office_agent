"""
任务规划器
根据用户指令自动拆解为多个子任务步骤
支持 LLM 智能规划和规则降级策略
"""
from typing import List, Dict, Any, Optional
import json
import logging
from langchain_community.llms import Tongyi
from config.settings import settings

logger = logging.getLogger(__name__)


class TaskPlanner:
    """任务规划器 - 将复杂任务拆解为可执行的步骤"""

    def __init__(self, llm: Optional[Tongyi] = None):
        self.llm = llm

    def plan(self, user_input: str, available_tools: List[str]) -> List[Dict[str, Any]]:
        """
        规划任务步骤：优先使用 LLM，失败时回退到规则
        """
        # 1. 尝试 LLM 规划
        if self.llm:
            llm_plan = self._llm_based_plan(user_input, available_tools)
            if llm_plan:
                return llm_plan
        # 2. 规则降级
        return self._rule_based_plan(user_input)

    def _llm_based_plan(self, user_input: str, available_tools: List[str]) -> Optional[List[Dict[str, Any]]]:
        """基于LLM进行规划，失败返回 None"""
        tools_str = ", ".join(available_tools)
        prompt = f"""你是一个任务规划专家。用户请求需要使用以下工具来完成任务：
可用工具：{tools_str}

用户请求：{user_input}

请分析请求，将任务拆解为具体的步骤。每个步骤必须使用上述工具之一，输出JSON格式的步骤列表。
示例格式：
[
    {{"tool": "data_analyzer", "params": {{"action": "read_data", "file_path": "data/sales_data.xlsx"}}}},
    {{"tool": "data_analyzer", "params": {{"action": "analyze"}}}},
    {{"tool": "data_analyzer", "params": {{"action": "generate_report", "auto_generate_doc": true}}}},
]

确保输出有效的JSON数组，不要包含任何额外文字。"""

        try:
            response = self.llm.invoke(prompt)
            start = response.find('[')
            end = response.rfind(']') + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                tasks = json.loads(json_str)
                logger.info(f"LLM规划生成 {len(tasks)} 个步骤")
                return tasks
        except Exception as e:
            logger.error(f"LLM规划失败: {e}")
        return None

    def _extract_file_path(self, user_input: str) -> str:
        """从用户输入中提取文件路径（供规则使用）"""
        import re
        patterns = [
            r'文件路径\s*[：:]\s*([^\s]+)',
            r'path\s*[：:]\s*([^\s]+)',
            r'文件\s*[：:]\s*([^\s]+)',
            r'(?:分析|查看|处理|使用|打开|读取|路径)?[：:\s]*(\S+\.(xlsx|xls|csv))',
            r'([^\s]+\.(xlsx|xls|csv))',
        ]
        for pattern in patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                return match.group(1)
        return "data/sales_data.xlsx"

    def _rule_based_plan(self, user_input: str) -> List[Dict[str, Any]]:
        """基于规则的规划（兜底）"""
        user_input_lower = user_input.lower()
        file_path = self._extract_file_path(user_input)

        if "分析" in user_input and ("excel" in user_input_lower or "数据" in user_input_lower or "销售" in user_input_lower):
            return [
                {"tool": "data_analyzer", "params": {"action": "read_data", "file_path": file_path}},
                {"tool": "data_analyzer", "params": {"action": "clean_data"}},
                {"tool": "data_analyzer", "params": {"action": "analyze"}},
                {"tool": "data_analyzer", "params": {"action": "visualize"}},
                {"tool": "data_analyzer", "params": {"action": "generate_report", "auto_generate_doc": True}}
            ]
        elif "报告" in user_input and "生成" in user_input:
            return [
                {"tool": "data_analyzer", "params": {"action": "read_data", "file_path": file_path}},
                {"tool": "data_analyzer", "params": {"action": "analyze"}},
                {"tool": "document_generator", "params": {"doc_type": "report", "auto_generate": True, "title": "数据分析报告"}}
            ]
        elif "会议纪要" in user_input or "会议记录" in user_input:
            return [
                {"tool": "document_generator", "params": {
                    "doc_type": "meeting_notes", "title": "会议纪要",
                    "auto_generate": True, "context": user_input
                }}
            ]
        elif "工作总结" in user_input or "周报" in user_input or "月报" in user_input:
            return [
                {"tool": "document_generator", "params": {
                    "doc_type": "work_summary", "title": "工作总结",
                    "auto_generate": True, "context": user_input
                }}
            ]
        elif "审批" in user_input or "申请" in user_input:
            system = "OA"
            approval_type = "leave"
            if "报销" in user_input: approval_type = "expense"
            elif "合同" in user_input: approval_type = "contract"
            elif "采购" in user_input: approval_type = "purchase"
            elif "出差" in user_input: approval_type = "travel"
            elif "加班" in user_input: approval_type = "overtime"
            return [{"tool": "api_tool", "params": {
                "action": "process_approval", "system": system,
                "approval_type": approval_type, "use_mock": True
            }}]
        elif "oa" in user_input_lower or "crm" in user_input_lower:
            system = "OA" if "oa" in user_input_lower else "CRM"
            if "状态" in user_input or "查看" in user_input:
                return [{"tool": "api_tool", "params": {"action": "get_system_status", "system": system}}]
            elif "审批" in user_input or "申请" in user_input:
                return [{"tool": "api_tool", "params": {
                    "action": "process_approval", "system": system,
                    "approval_type": "leave", "use_mock": True
                }}]
        elif "知识" in user_input or "制度" in user_input or "政策" in user_input or "产品" in user_input:
            return [{"tool": "knowledge_qa", "params": {"question": user_input}}]
        else:
            # 默认使用知识问答
            return [{"tool": "knowledge_qa", "params": {"question": user_input}}]
