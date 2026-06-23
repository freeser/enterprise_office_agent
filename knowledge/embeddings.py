"""
Embedding 模型加载模块
支持从 HuggingFace 加载本地或在线模型，路径不存在时自动回退
"""
import os
import logging
from langchain_huggingface import HuggingFaceEmbeddings
from config.settings import settings

logger = logging.getLogger(__name__)

def get_embeddings(model_name: str = None) -> HuggingFaceEmbeddings:
    model = model_name or settings.EMBEDDING_MODEL_NAME

    # 检查本地路径是否存在
    if os.path.exists(model):
        logger.info(f"使用本地 Embedding 模型: {model}")
    else:
        logger.warning(f"本地模型路径不存在: {model}，自动切换到在线模型 BAAI/bge-small-zh-v1.5")
        model = "BAAI/bge-small-zh-v1.5"

    return HuggingFaceEmbeddings(
        model_name=model,
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )