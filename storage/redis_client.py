"""
Redis 客户端封装
用于缓存会话上下文、工具调用结果、临时数据等
"""
import redis
import json
from typing import Optional, Any, List
import logging

from config.settings import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis 客户端封装"""
    
    def __init__(self):
        try:
            self.client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            self.client.ping()
            self.available = True
            logger.info("Redis 连接成功")
        except Exception as e:
            logger.warning(f"Redis 连接失败: {e}，将使用内存存储降级")
            self.client = None
            self.available = False
            self._fallback_storage = {}
    
    def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """设置键值（支持JSON序列化）"""
        try:
            serialized = json.dumps(value, ensure_ascii=False)
            if self.available:
                self.client.set(key, serialized, ex=expire)
            else:
                self._fallback_storage[key] = {"value": serialized, "expire": expire}
            return True
        except Exception as e:
            logger.error(f"Redis set 失败: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """获取键值（自动JSON反序列化）"""
        try:
            if self.available:
                value = self.client.get(key)
            else:
                item = self._fallback_storage.get(key)
                value = item["value"] if item else None
            
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Redis get 失败: {e}")
            return None
    
    def delete(self, *keys: str) -> int:
        """删除键"""
        try:
            if self.available:
                return self.client.delete(*keys)
            else:
                count = 0
                for key in keys:
                    if key in self._fallback_storage:
                        del self._fallback_storage[key]
                        count += 1
                return count
        except Exception as e:
            logger.error(f"Redis delete 失败: {e}")
            return 0
    
    def keys(self, pattern: str) -> List[str]:
        """获取匹配模式的所有键"""
        try:
            if self.available:
                return self.client.keys(pattern)
            else:
                import fnmatch
                return [k for k in self._fallback_storage.keys() if fnmatch.fnmatch(k, pattern)]
        except Exception as e:
            logger.error(f"Redis keys 失败: {e}")
            return []
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            if self.available:
                return self.client.exists(key) > 0
            else:
                return key in self._fallback_storage
        except Exception as e:
            logger.error(f"Redis exists 失败: {e}")
            return False
    
    def lpush(self, key: str, *values: Any) -> int:
        """向列表左侧添加元素"""
        try:
            serialized = [json.dumps(v, ensure_ascii=False) for v in values]
            if self.available:
                return self.client.lpush(key, *serialized)
            else:
                if key not in self._fallback_storage:
                    self._fallback_storage[key] = []
                self._fallback_storage[key] = list(values) + self._fallback_storage[key]
                return len(self._fallback_storage[key])
        except Exception as e:
            logger.error(f"Redis lpush 失败: {e}")
            return 0
    
    def lrange(self, key: str, start: int, end: int) -> List[Any]:
        """获取列表指定范围元素"""
        try:
            if self.available:
                values = self.client.lrange(key, start, end)
                return [json.loads(v) for v in values]
            else:
                lst = self._fallback_storage.get(key, [])
                return lst[start:end+1] if end >= 0 else lst[start:]
        except Exception as e:
            logger.error(f"Redis lrange 失败: {e}")
            return []
    
    def ltrim(self, key: str, start: int, end: int) -> bool:
        """修剪列表"""
        try:
            if self.available:
                self.client.ltrim(key, start, end)
            else:
                if key in self._fallback_storage:
                    lst = self._fallback_storage[key]
                    self._fallback_storage[key] = lst[start:end+1] if end >= 0 else lst[start:]
            return True
        except Exception as e:
            logger.error(f"Redis ltrim 失败: {e}")
            return False