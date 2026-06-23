"""
反思模块
任务执行失败时的自我反思与策略调整
"""
from typing import List, Dict, Any, Optional
import json
import logging

from langchain_community.llms import Tongyi

logger = logging.getLogger(__name__)


class Reflection:
    """反思器 - 分析失败原因并生成替代策略"""
    
    def __init__(self, llm: Optional[Tongyi] = None):
        self.llm = llm
        self.max_retries = 3
    
    def analyze_failure(self, task: Dict[str, Any], error: str) -> Dict[str, Any]:
        """
        分析单个任务失败原因，返回调整后的任务参数
        
        Args:
            task: 失败的任务字典
            error: 错误信息
        
        Returns:
            调整后的任务（可能是原参数或修改后的参数）
        """
        if self.llm:
            return self._llm_based_analyze(task, error)
        else:
            return self._rule_based_analyze(task, error)
    
    def _llm_based_analyze(self, task: Dict[str, Any], error: str) -> Dict[str, Any]:
        """基于LLM分析"""
        prompt = f"""任务执行失败，请分析错误原因并提供修正后的任务参数。
原始任务：{json.dumps(task, ensure_ascii=False)}
错误信息：{error}

请返回一个JSON对象，包含 tool 和修正后的 params。例如：
{{"tool": "data_analyzer", "params": {{"action": "read_data", "file_path": "data/sales_data.xlsx"}}}}
确保只返回有效的JSON。"""
        
        try:
            response = self.llm.invoke(prompt)
            # 提取JSON对象
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                adjusted = json.loads(response[start:end])
                return adjusted
        except Exception as e:
            logger.error(f"LLM反思分析失败: {e}")
        
        # 降级：返回原任务（可增加简单修正）
        return self._rule_based_analyze(task, error)
    
    def _rule_based_analyze(self, task: Dict[str, Any], error: str) -> Dict[str, Any]:
        """基于规则修正"""
        adjusted = task.copy()
        error_lower = error.lower()
        
        if task["tool"] == "data_analyzer":
            if "file" in error_lower and ("not found" in error_lower or "不存在" in error):
                adjusted["params"]["file_path"] = "data/sales_data.xlsx"
            elif "action" in error_lower:
                adjusted["params"]["action"] = "read_data"  # 确保有效action
        
        elif task["tool"] == "api_tool":
            if "system" in error_lower:
                adjusted["params"]["system"] = "OA"  # 默认使用OA
        
        return adjusted
    
    def should_retry(self, error: str, retry_count: int) -> bool:
        """判断是否应该重试"""
        if retry_count >= self.max_retries:
            return False
        
        retryable_errors = ["timeout", "connection", "network", "暂时", "超时", "重试"]
        error_lower = error.lower()
        return any(err in error_lower for err in retryable_errors)
    
    def generate_alternative_plan(self, original_tasks: List[Dict], error_context: str) -> List[Dict]:
        """
        当整体任务失败时，生成替代执行计划
        
        Args:
            original_tasks: 原始任务列表
            error_context: 错误上下文
        
        Returns:
            替代任务列表
        """
        if self.llm:
            prompt = f"""原始任务计划遇到问题，请生成一个替代方案。
原始计划：{json.dumps(original_tasks, ensure_ascii=False)}
错误描述：{error_context}

请返回一个新的任务步骤列表，JSON数组格式。"""
            try:
                response = self.llm.invoke(prompt)
                start = response.find('[')
                end = response.rfind(']') + 1
                if start != -1 and end > start:
                    return json.loads(response[start:end])
            except Exception as e:
                logger.error(f"LLM替代计划生成失败: {e}")
        
        # 降级：返回简化计划
        return [
            {"tool": "knowledge_qa", "params": {"question": error_context}}
        ]
    
    def reflect_on_execution(self, tasks: List[Dict], results: List[Any]) -> str:
        """对整个执行过程进行反思，输出总结经验"""
        if self.llm:
            prompt = f"""请对以下任务执行过程进行反思总结，指出成功之处和可改进点。
任务：{json.dumps(tasks, ensure_ascii=False)}
结果：{results}

总结："""
            try:
                return self.llm.invoke(prompt).strip()
            except Exception as e:
                logger.error(f"LLM反思总结失败: {e}")
        
        # 简单统计
        success = sum(1 for r in results if not str(r).startswith("Error") and "失败" not in str(r))
        return f"任务执行完成：成功 {success} 项，失败 {len(results)-success} 项。"