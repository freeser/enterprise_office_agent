"""
核心Agent封装
基于LangChain ReAct Agent，集成记忆、工具调用、反思功能
支持复杂任务的自动规划与多步骤执行
"""
import os
import uuid
from typing import Optional, List, Dict, Any
import logging

from langchain_classic.agents import AgentExecutor
from langchain_classic.agents.react.agent import create_react_agent

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_classic.memory import ConversationBufferWindowMemory

from config.settings import settings
from .memory_manager import MemoryManager
from .tool_registry import ToolRegistry
from .reflection import Reflection
from .planner import TaskPlanner

logger = logging.getLogger(__name__)


class CustomConversationMemory(ConversationBufferWindowMemory):
    """扩展记忆类，在保存上下文时同步到 MemoryManager，并避免多 key 警告"""
    memory_manager: MemoryManager = None
    session_id: str = ""

    class Config:
        arbitrary_types_allowed = True

    def save_context(self, inputs: dict, outputs: dict) -> None:
        output_text = outputs.get("output", "")
        clean_outputs = {"output": output_text}
        super().save_context(inputs, clean_outputs)

        if self.memory_manager:
            user_input = inputs.get("input", "")
            if user_input:
                self.memory_manager.add_message(self.session_id, "user", user_input)
            if output_text:
                self.memory_manager.add_message(self.session_id, "assistant", output_text)


class OfficeAgent:
    REACT_TEMPLATE = """你是一个企业智能办公助手，能够使用各种工具帮助用户完成办公任务。

你可以使用的工具有：
{tools}

工具名称列表：{tool_names}

请严格按照以下格式回答：

Question: 用户的问题
Thought: 思考需要做什么
Action: 要使用的工具名称（必须是 [{tool_names}] 中的一个）
Action Input: 工具的输入参数（JSON格式）
Observation: 工具返回的结果
... (这个 Thought/Action/Action Input/Observation 可以重复多次)
Thought: 我现在知道最终答案了
Final Answer: 对用户的最终回复

开始！

历史对话：
{chat_history}

Question: {input}
Thought: {agent_scratchpad}"""

    def __init__(self, llm: Optional[ChatOpenAI] = None, enable_planner: bool = True):
        if llm:
            self.llm = llm
        else:
            self._init_llm()

        self.memory_manager = MemoryManager()
        self.tool_registry = ToolRegistry()
        self.reflection = Reflection(self.llm)
        self.agent_executor: Optional[AgentExecutor] = None
        self.enable_planner = enable_planner and (self.llm is not None)
        if self.enable_planner:
            self.task_planner = TaskPlanner(self.llm)
        logger.info(f"OfficeAgent初始化完成，Planner模式: {'开启' if self.enable_planner else '关闭'}")

    def _init_llm(self):
        if settings.DASHSCOPE_API_KEY:
            os.environ["DASHSCOPE_API_KEY"] = settings.DASHSCOPE_API_KEY
            self.llm = ChatOpenAI(
                model=settings.LLM_MODEL_NAME,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                api_key=settings.DASHSCOPE_API_KEY,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )
            logger.info(f"LLM初始化成功，模型: {settings.LLM_MODEL_NAME}")
        else:
            logger.warning("未配置API Key，Agent将无法正常工作")
            self.llm = None

    def register_tool(self, tool):
        self.tool_registry.register(tool)

    def register_tools(self, tools: List):
        self.tool_registry.register_many(tools)

    def _create_agent_executor(self, session_id: str) -> AgentExecutor:
        tools = self.tool_registry.list_tools()
        if not tools:
            raise ValueError("没有注册任何工具，请先注册工具")

        prompt = PromptTemplate.from_template(self.REACT_TEMPLATE)
        memory = CustomConversationMemory(
            memory_key="chat_history",
            return_messages=False,
            input_key="input",
            k=settings.SHORT_TERM_MEMORY_MAX_LENGTH,
            memory_manager=self.memory_manager,
            session_id=session_id
        )

        history = self.memory_manager.get_messages(session_id)
        for msg in history:
            if msg["role"] == "user":
                memory.chat_memory.add_user_message(msg["content"])
            else:
                memory.chat_memory.add_ai_message(msg["content"])

        agent = create_react_agent(llm=self.llm, tools=tools, prompt=prompt)
        executor = AgentExecutor(
            agent=agent, tools=tools, memory=memory,
            verbose=settings.DEBUG, handle_parsing_errors=True,
            max_iterations=8, return_intermediate_steps=True
        )
        return executor

    def _is_complex_task(self, user_input: str) -> bool:
        complex_keywords = ["分析", "报告", "生成", "图表", "可视化", "工作总结", "会议纪要", "审批"]
        return any(kw in user_input for kw in complex_keywords)

    # LLM 常见参数名 → 工具实际参数名的映射（用于自动纠错）
    PARAM_ALIASES: Dict[str, Dict[str, str]] = {
        "knowledge_qa": {
            "query": "question",
            "query_text": "question",
            "input": "question",
        },
        "document_generator": {
            "action": "doc_type",
            "type": "doc_type",
        },
        "api_tool": {},
        "data_analyzer": {},
    }

    def _normalize_params(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """将 LLM 生成的不规范参数名映射为工具实际需要的参数名"""
        aliases = self.PARAM_ALIASES.get(tool_name, {})
        if not aliases:
            return params

        normalized = dict(params)
        for llm_name, real_name in aliases.items():
            if llm_name in normalized and real_name not in normalized:
                normalized[real_name] = normalized.pop(llm_name)
                logger.info(f"参数名自动纠错: {tool_name}.{llm_name} → {real_name}")
        return normalized

    def _build_tool_schemas(self) -> Dict[str, Any]:
        """构建工具 Schema 字典供 Planner 使用"""
        schemas = {}
        for tool in self.tool_registry.list_tools():
            info = {"description": tool.description}
            if hasattr(tool, 'args_schema') and tool.args_schema is not None:
                try:
                    json_schema = tool.args_schema.model_json_schema()
                    info["properties"] = json_schema.get("properties", {})
                    info["required"] = json_schema.get("required", [])
                except Exception as e:
                    logger.warning(f"无法获取工具 {tool.name} 的 Schema: {e}")
                    info["properties"] = {}
                    info["required"] = []
            schemas[tool.name] = info
        return schemas

    def _execute_planned_task(self, user_input: str, session_id: str,
                               user_id: Optional[str] = None) -> Dict[str, Any]:
        """多步骤任务执行（使用规划器）"""
        available_tools = self.tool_registry.get_tool_names()
        tool_schemas = self._build_tool_schemas()
        task_steps = self.task_planner.plan(user_input, available_tools, tool_schemas)
        if not task_steps:
            return self._execute_single_step(user_input, session_id, user_id)

        logger.info(f"任务规划成功，共 {len(task_steps)} 个步骤")
        all_steps = []
        final_output = ""

        for i, step in enumerate(task_steps):
            tool_name = step.get("tool")
            params = step.get("params", {})
            logger.info(f"执行步骤 {i+1}/{len(task_steps)}: {tool_name}")

            tool = self.tool_registry.get_tool(tool_name)
            if not tool:
                error_msg = f"错误：未找到工具 {tool_name}"
                all_steps.append({"step": i+1, "tool": tool_name, "error": error_msg})
                final_output += f"\n[步骤{i+1} 失败] {error_msg}"
                continue

            # 参数名自动纠错
            params = self._normalize_params(tool_name, params)

            try:
                observation = tool.invoke(params)
                all_steps.append({
                    "tool": tool_name,
                    "tool_input": params,
                    "observation": observation
                })
                final_output += f"\n[步骤{i+1} 完成] {tool_name}: {observation[:200]}"
                self.memory_manager.mysql.log_tool_call(
                    session_id=session_id,
                    user_id=user_id or "anonymous",
                    tool_name=tool_name,
                    params=params,
                    result=str(observation)[:1000]
                )
            except Exception as e:
                error_msg = f"执行出错: {str(e)}"
                logger.error(f"步骤 {i+1} 执行失败: {e}")
                all_steps.append({"step": i+1, "tool": tool_name, "error": error_msg})
                final_output += f"\n[步骤{i+1} 出错] {error_msg}"

        return {
            "output": final_output.strip() or "任务执行完成",
            "intermediate_steps": all_steps,
            "session_id": session_id,
            "planned": True,
            "steps_count": len(task_steps)
        }

    def _execute_single_step(self, user_input: str, session_id: str,
                             user_id: Optional[str] = None) -> Dict[str, Any]:
        """单步任务（ReAct Agent）"""
        try:
            executor = self._create_agent_executor(session_id)
            user_context = ""
            if user_id:
                prefs = self.memory_manager.get_all_preferences(user_id)
                if prefs:
                    user_context = f"\n用户偏好信息：{prefs}"

            result = executor.invoke({"input": user_input + user_context})
            steps = result.get("intermediate_steps", [])
            for step in steps:
                if len(step) >= 2:
                    action, observation = step[0], step[1]
                    self.memory_manager.mysql.log_tool_call(
                        session_id=session_id,
                        user_id=user_id or "anonymous",
                        tool_name=action.tool,
                        params=action.tool_input,
                        result=str(observation)[:1000]
                    )
            return {
                "output": result.get("output", "执行完成"),
                "intermediate_steps": steps,
                "session_id": session_id,
                "planned": False
            }
        except Exception as e:
            logger.error(f"单步执行失败: {e}", exc_info=True)
            return {
                "output": f"执行失败: {str(e)}",
                "intermediate_steps": [],
                "session_id": session_id,
                "error": str(e)
            }

    def run(self, user_input: str, session_id: Optional[str] = None,
            user_id: Optional[str] = None, use_planner: bool = None) -> Dict[str, Any]:
        if session_id is None:
            session_id = str(uuid.uuid4())
        if not self.llm:
            return {
                "output": "LLM未初始化，请配置API Key后重试。",
                "intermediate_steps": [],
                "session_id": session_id
            }
        if use_planner is None:
            use_planner = self.enable_planner and self._is_complex_task(user_input)
        if use_planner:
            logger.info("使用任务规划器处理请求")
            return self._execute_planned_task(user_input, session_id, user_id)
        else:
            logger.info("使用ReAct Agent处理请求")
            return self._execute_single_step(user_input, session_id, user_id)

    def clear_session(self, session_id: str):
        self.memory_manager.clear_session(session_id)