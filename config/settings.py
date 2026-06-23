"""
配置管理模块
使用 Pydantic Settings 管理所有配置项，支持从环境变量读取
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """应用配置类"""
    
    # ========== 应用基础配置 ==========
    APP_NAME: str = "Enterprise Intelligent Office Assistant"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True
    
    # ========== LLM 配置 ==========
    # 通义千问 API 配置（可通过环境变量 DASHSCOPE_API_KEY 设置）
    DASHSCOPE_API_KEY: Optional[str] = None
    LLM_MODEL_NAME: str = "qwen-plus"  # 可选: qwen-turbo, qwen-plus, qwen-max
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2000
    
    # 备用本地模型路径（如果不用通义千问，可切换到本地模型）
    LOCAL_EMBEDDING_MODEL: str = "models/bge_small_zh"
    
    # ========== 数据库配置 ==========
    # MySQL
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "password"
    MYSQL_DATABASE: str = "office_assistant"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # ========== 向量数据库配置 ==========
    CHROMA_PERSIST_DIR: str = "data/chroma_db"
    EMBEDDING_MODEL_NAME: str = "models/bge_small_zh"  # 中文Embedding模型
    
    # ========== 工具配置 ==========
    # 数据分析工具
    DEFAULT_DATA_PATH: str = "data/sales_data.xlsx"
    VISUALIZATION_OUTPUT_DIR: str = "data/visualizations"
    
    # 文档生成工具
    DOCUMENT_OUTPUT_DIR: str = "data/documents"
    
    # API 工具 (模拟企业内部系统)
    OA_API_BASE_URL: str = "http://localhost:8000/api/oa"
    CRM_API_BASE_URL: str = "http://localhost:8000/api/crm"
    
    # 知识库
    KNOWLEDGE_BASE_DIR: str = "data/knowledge_base"
    
    # ========== 记忆模块配置 ==========
    SHORT_TERM_MEMORY_MAX_LENGTH: int = 10  # 短期记忆最大保留条数
    LONG_TERM_MEMORY_PREFIX: str = "user_memory:"  # Redis key前缀
    
    # ========== 反思模块配置 ==========
    MAX_RETRY_COUNT: int = 3  # 最大重试次数
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# 创建全局配置实例
settings = Settings()

# 确保必要的目录存在
os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
os.makedirs(settings.VISUALIZATION_OUTPUT_DIR, exist_ok=True)
os.makedirs(settings.DOCUMENT_OUTPUT_DIR, exist_ok=True)
os.makedirs(settings.KNOWLEDGE_BASE_DIR, exist_ok=True)