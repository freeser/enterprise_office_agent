"""
记忆管理器
统一管理短期记忆（会话上下文）和长期记忆（用户偏好）
支持Redis持久化，失败时降级为内存存储
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import logging

from storage import RedisClient, MySQLClient
from config.settings import settings

logger = logging.getLogger(__name__)


class MemoryManager:
    def __init__(self):
        self.redis = RedisClient()
        self.mysql = MySQLClient()
        self._short_term_cache: Dict[str, List[Dict[str, Any]]] = {}

    def add_message(self, session_id: str, role: str, content: str) -> None:
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        key = f"chat:{session_id}"

        # Redis 存储
        self.redis.lpush(key, message)
        self.redis.ltrim(key, 0, settings.SHORT_TERM_MEMORY_MAX_LENGTH - 1)

        # MySQL 持久化
        self.mysql.add_conversation(session_id, role, content)

        # 降级缓存：无论 Redis 是否可用，都维护本地列表
        if session_id not in self._short_term_cache:
            self._short_term_cache[session_id] = []
        self._short_term_cache[session_id].append(message)
        if len(self._short_term_cache[session_id]) > settings.SHORT_TERM_MEMORY_MAX_LENGTH:
            self._short_term_cache[session_id] = self._short_term_cache[session_id][-settings.SHORT_TERM_MEMORY_MAX_LENGTH:]

    def get_messages(self, session_id: str, limit: int = None) -> List[Dict[str, Any]]:
        key = f"chat:{session_id}"
        messages = []

        if self.redis.available:
            raw_msgs = self.redis.lrange(key, 0, -1)
            messages = list(reversed(raw_msgs))
        elif session_id in self._short_term_cache:
            messages = self._short_term_cache[session_id].copy()
        else:
            # 从 MySQL 获取并加载到缓存
            db_msgs = self.mysql.get_conversation_history(session_id, limit or 20)
            for msg in db_msgs:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": msg["created_at"].isoformat() if hasattr(msg["created_at"], "isoformat") else str(msg["created_at"])
                })
            self._short_term_cache[session_id] = messages.copy()

        if limit:
            messages = messages[-limit:]
        return messages

    def get_chat_history_string(self, session_id: str, limit: int = 6) -> str:
        messages = self.get_messages(session_id, limit)
        if not messages:
            return "（无历史对话）"
        lines = [f"{'用户' if m['role']=='user' else '助手'}: {m['content']}" for m in messages]
        return "\n".join(lines)

    def clear_session(self, session_id: str) -> None:
        key = f"chat:{session_id}"
        self.redis.delete(key)
        self._short_term_cache.pop(session_id, None)
        logger.info(f"会话 {session_id} 记忆已清除")
    
    # ========== 长期记忆（用户偏好）==========
    def set_preference(self, user_id: str, key: str, value: Any) -> bool:
        """
        设置用户偏好
        
        Args:
            user_id: 用户ID
            key: 偏好键
            value: 偏好值
        
        Returns:
            是否成功
        """
        # 存入Redis
        redis_key = f"{settings.LONG_TERM_MEMORY_PREFIX}{user_id}:{key}"
        self.redis.set(redis_key, value)
        # 存入MySQL
        return self.mysql.set_preference(user_id, key, json.dumps(value, ensure_ascii=False))
    
    def get_preference(self, user_id: str, key: str, default: Any = None) -> Any:
        """
        获取用户偏好
        
        Args:
            user_id: 用户ID
            key: 偏好键
            default: 默认值
        
        Returns:
            偏好值
        """
        # 优先从Redis获取
        redis_key = f"{settings.LONG_TERM_MEMORY_PREFIX}{user_id}:{key}"
        value = self.redis.get(redis_key)
        if value is not None:
            return value
        
        # 从MySQL获取
        db_value = self.mysql.get_preference(user_id, key)
        if db_value is not None:
            try:
                return json.loads(db_value)
            except:
                return db_value
        
        return default
    
    def get_all_preferences(self, user_id: str) -> Dict[str, Any]:
        """获取用户所有偏好"""
        prefs = self.mysql.get_all_preferences(user_id)
        result = {}
        for k, v in prefs.items():
            try:
                result[k] = json.loads(v)
            except:
                result[k] = v
        return result
    
    # ========== 记忆摘要（用于上下文压缩）==========
    def generate_summary(self, session_id: str, llm=None) -> str:
        """
        生成会话摘要（调用LLM总结对话）
        
        Args:
            session_id: 会话ID
            llm: LLM实例
        
        Returns:
            摘要字符串
        """
        messages = self.get_messages(session_id, limit=20)
        if not messages or not llm:
            return "会话暂无足够内容"
        
        conversation = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        prompt = f"""请对以下对话进行简洁的摘要总结，突出关键信息和用户需求。
对话内容：
{conversation}

摘要："""
        
        try:
            summary = llm.invoke(prompt)
            self.set_preference(f"session:{session_id}", "summary", summary)
            return summary.strip()
        except Exception as e:
            logger.error(f"生成摘要失败: {e}")
            return "摘要生成失败"