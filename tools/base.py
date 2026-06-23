"""
工具基类定义
所有自定义工具都继承自 LangChain 的 BaseTool
"""
from langchain_core.tools import BaseTool as LangChainBaseTool
from abc import abstractmethod
from typing import Any, Optional, Type
from pydantic import BaseModel


class BaseTool(LangChainBaseTool):
    """
    工具基类，扩展了 LangChain BaseTool
    
    子类需要实现：
    - name: 工具名称
    - description: 工具描述
    - _execute: 具体的业务逻辑（接收参数）
    - _run: 同步执行方法（已自动处理参数）
    - _arun: 异步执行方法（可选）
    - args_schema: Pydantic 参数模型（可选）
    """
    
    # 重写 _run，兼容 LangChain 可能传入的 *args 和 **kwargs
    def _run(self, *args: Any, **kwargs: Any) -> str:
        """
        工具调用入口
        LangChain 会根据 args_schema 将参数自动解析为 kwargs，
        但某些情况下也可能传入位置参数，因此这里做了兼容。
        """
        try:
            # 如果子类实现了 _execute，将参数全部传递
            return self._execute(*args, **kwargs)
        except Exception as e:
            return f"工具执行出错: {str(e)}"
    
    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        """异步执行（默认调用同步方法）"""
        return self._run(*args, **kwargs)
    
    @abstractmethod
    def _execute(self, *args, **kwargs) -> str:
        """子类实现具体的工具逻辑"""
        pass