"""
知识检索器封装
支持从向量数据库检索相关内容，并可结合重排序等优化
"""
from typing import List, Optional
from langchain_core.documents import Document

from .vector_store import VectorStoreManager


class KnowledgeRetriever:
    """知识库检索器"""
    
    def __init__(self, collection_name: str = "enterprise_knowledge"):
        """
        初始化检索器
        
        Args:
            collection_name: 向量数据库集合名称
        """
        self.vector_store = VectorStoreManager(collection_name)
    
    def retrieve(self, query: str, top_k: int = 4) -> List[Document]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
        
        Returns:
            Document 列表
        """
        return self.vector_store.similarity_search(query, k=top_k)
    
    def retrieve_with_scores(self, query: str, top_k: int = 4) -> List[tuple]:
        """
        检索相关文档并返回相似度分数
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
        
        Returns:
            (Document, score) 元组列表
        """
        return self.vector_store.similarity_search_with_score(query, k=top_k)
    
    def get_relevant_context(self, query: str, top_k: int = 4) -> str:
        """
        获取格式化的上下文文本，可直接用于 Prompt
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
        
        Returns:
            拼接后的上下文字符串
        """
        docs = self.retrieve(query, top_k)
        if not docs:
            return "知识库中未找到相关信息。"
        
        context_parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "未知来源")
            context_parts.append(f"[参考资料 {i} 来源: {source}]\n{doc.page_content}")
        
        return "\n\n".join(context_parts)
    
    def as_langchain_retriever(self, search_kwargs: dict = None):
        """
        转换为 LangChain 兼容的检索器
        
        Args:
            search_kwargs: 检索参数
        
        Returns:
            Retriever 实例
        """
        return self.vector_store.as_retriever(search_kwargs)