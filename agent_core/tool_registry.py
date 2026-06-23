"""
工具注册中心
管理所有可用工具，支持动态注册和获取
"""
from typing import List, Dict, Optional
from langchain_core.tools import BaseTool
import logging

logger = logging.getLogger(__name__)


class ToolRegistry:
    """工具注册中心"""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool) -> None:
        """
        注册工具
        
        Args:
            tool: LangChain BaseTool实例
        """
        self._tools[tool.name] = tool
        logger.info(f"工具已注册: {tool.name}")
    
    def register_many(self, tools: List[BaseTool]) -> None:
        """批量注册工具"""
        for tool in tools:
            self.register(tool)
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """获取指定名称的工具"""
        return self._tools.get(name)
    
    def list_tools(self) -> List[BaseTool]:
        """获取所有工具列表"""
        return list(self._tools.values())
    
    def get_tool_names(self) -> List[str]:
        """获取所有工具名称"""
        return list(self._tools.keys())
    
    def get_tools_description(self) -> str:
        """获取所有工具的描述文本，用于Prompt"""
        if not self._tools:
            return "暂无可用工具"
        
        lines = []
        for name, tool in self._tools.items():
            lines.append(f"- {name}: {tool.description}")
        return "\n".join(lines)
    
    def clear(self) -> None:
        """清空所有注册的工具"""
        self._tools.clear()
        logger.info("所有工具已清空")