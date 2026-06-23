"""
向量数据库管理模块
"""
import os
import logging
from typing import List, Optional
from langchain_chroma import Chroma
from langchain_core.documents import Document

from config.settings import settings
from .embeddings import get_embeddings

logger = logging.getLogger(__name__)


class VectorStoreManager:
    def __init__(self, collection_name: str = "enterprise_knowledge"):
        self.collection_name = collection_name
        self.persist_directory = os.path.join(settings.CHROMA_PERSIST_DIR, collection_name)
        os.makedirs(self.persist_directory, exist_ok=True)

        self.embeddings = get_embeddings()
        self.vectorstore = None
        self._init_vectorstore()

    def _init_vectorstore(self):
        """安全初始化 Chroma 向量存储"""
        try:
            self.vectorstore = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory
            )
            logger.info(f"向量数据库初始化成功，集合: {self.collection_name}")
        except Exception as e:
            logger.error(f"向量数据库初始化失败: {e}", exc_info=True)
            self.vectorstore = None
            # 你可以在此处提供更友好的提示，例如：
            # print("向量数据库不可用，请联系管理员")

    def ensure_ready(self):
        """如果之前初始化失败，可以重新尝试一次"""
        if self.vectorstore is None:
            self._init_vectorstore()
        return self.vectorstore is not None

    def add_documents(self, documents: List[Document]) -> bool:
        if not self.ensure_ready():
            logger.error("向量数据库未初始化，无法添加文档")
            return False
        try:
            self.vectorstore.add_documents(documents)
            # Chroma 新版本不再需要手动 persist，自动持久化
            logger.info(f"成功添加 {len(documents)} 个文档片段")
            return True
        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            return False

    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        if not self.ensure_ready():
            return []
        try:
            return self.vectorstore.similarity_search(query, k=k)
        except Exception as e:
            logger.error(f"相似度搜索失败: {e}")
            return []

    def similarity_search_with_score(self, query: str, k: int = 4) -> List[tuple]:
        if not self.ensure_ready():
            return []
        try:
            return self.vectorstore.similarity_search_with_score(query, k=k)
        except Exception as e:
            logger.error(f"相似度搜索失败: {e}")
            return []

    def delete_collection(self) -> bool:
        if not self.ensure_ready():
            return False
        try:
            self.vectorstore.delete_collection()
            logger.info(f"集合 {self.collection_name} 已删除")
            # 删除集合后将vectorstore设置为None，以便下次使用时重新初始化
            self.vectorstore = None
            return True
        except Exception as e:
            logger.error(f"删除集合失败: {e}")
            return False

    def get_document_count(self) -> int:
        if not self.ensure_ready():
            return 0
        try:
            collection_data = self.vectorstore.get()
            return len(collection_data.get("documents", []))
        except Exception:
            return 0

    def as_retriever(self, search_kwargs: dict = None):
        if not self.ensure_ready():
            return None
        return self.vectorstore.as_retriever(search_kwargs=search_kwargs or {"k": 4})