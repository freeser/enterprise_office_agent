"""
MySQL 数据库操作封装
用于存储用户偏好、工具调用记录等结构化数据
"""
import pymysql
from pymysql.cursors import DictCursor
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import logging

from config.settings import settings

logger = logging.getLogger(__name__)


class MySQLClient:
    """MySQL 客户端封装"""
    
    def __init__(self):
        self.config = {
            "host": settings.MYSQL_HOST,
            "port": settings.MYSQL_PORT,
            "user": settings.MYSQL_USER,
            "password": settings.MYSQL_PASSWORD,
            "database": settings.MYSQL_DATABASE,
            "charset": "utf8mb4",
            "cursorclass": DictCursor,
            "autocommit": True
        }
        self._ensure_database()
        self._init_tables()

    def _ensure_database(self):
        """确保数据库存在，不存在则创建"""
        # 改成不指定数据库，连接后创建
        create_config = self.config.copy()
        db_name = create_config.pop("database")
        try:
            conn = pymysql.connect(**create_config)
            with conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4")
            conn.close()
        except Exception as e:
            logger.warning(f"无法自动创建数据库 {db_name}: {e}，请手动创建")
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = pymysql.connect(**self.config)
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_tables(self):
        """初始化数据库表（如果不存在）"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS user_preferences (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(100) NOT NULL,
            pref_key VARCHAR(100) NOT NULL,
            pref_value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_user_pref (user_id, pref_key)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            session_id VARCHAR(100) NOT NULL,
            role ENUM('user', 'assistant') NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_session (session_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        
        CREATE TABLE IF NOT EXISTS tool_call_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            session_id VARCHAR(100),
            user_id VARCHAR(100),
            tool_name VARCHAR(100) NOT NULL,
            params JSON,
            result TEXT,
            error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_session (session_id),
            INDEX idx_user (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    for stmt in create_table_sql.strip().split(';'):
                        if stmt.strip():
                            cursor.execute(stmt)
        except Exception as e:
            logger.warning(f"初始化MySQL表失败: {e}，将使用降级模式")
    
    # ========== 用户偏好操作 ==========
    def set_preference(self, user_id: str, key: str, value: str) -> bool:
        """设置用户偏好"""
        sql = """
        INSERT INTO user_preferences (user_id, pref_key, pref_value)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE pref_value = VALUES(pref_value)
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (user_id, key, value))
            return True
        except Exception as e:
            logger.error(f"设置用户偏好失败: {e}")
            return False
    
    def get_preference(self, user_id: str, key: str) -> Optional[str]:
        """获取用户偏好"""
        sql = "SELECT pref_value FROM user_preferences WHERE user_id = %s AND pref_key = %s"
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (user_id, key))
                    row = cursor.fetchone()
                    return row["pref_value"] if row else None
        except Exception as e:
            logger.error(f"获取用户偏好失败: {e}")
            return None
    
    def get_all_preferences(self, user_id: str) -> Dict[str, str]:
        """获取用户所有偏好"""
        sql = "SELECT pref_key, pref_value FROM user_preferences WHERE user_id = %s"
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (user_id,))
                    rows = cursor.fetchall()
                    return {row["pref_key"]: row["pref_value"] for row in rows}
        except Exception as e:
            logger.error(f"获取用户所有偏好失败: {e}")
            return {}
    
    def delete_preference(self, user_id: str, key: str) -> bool:
        """删除用户偏好"""
        sql = "DELETE FROM user_preferences WHERE user_id = %s AND pref_key = %s"
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (user_id, key))
            return True
        except Exception as e:
            logger.error(f"删除用户偏好失败: {e}")
            return False
    
    # ========== 对话历史操作 ==========
    def add_conversation(self, session_id: str, role: str, content: str) -> bool:
        """添加对话记录"""
        sql = "INSERT INTO conversation_history (session_id, role, content) VALUES (%s, %s, %s)"
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (session_id, role, content))
            return True
        except Exception as e:
            logger.error(f"添加对话记录失败: {e}")
            return False
    
    def get_conversation_history(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """获取对话历史"""
        sql = """
        SELECT role, content, created_at 
        FROM conversation_history 
        WHERE session_id = %s 
        ORDER BY created_at DESC 
        LIMIT %s
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (session_id, limit))
                    rows = cursor.fetchall()
                    # 按时间正序返回（最早的在前）
                    return list(reversed(rows))
        except Exception as e:
            logger.error(f"获取对话历史失败: {e}")
            return []
    
    # ========== 工具调用日志 ==========
    def log_tool_call(self, session_id: str, user_id: str, tool_name: str, 
                      params: Dict, result: Any, error: Optional[str] = None) -> bool:
        """记录工具调用日志"""
        import json
        sql = """
        INSERT INTO tool_call_logs (session_id, user_id, tool_name, params, result, error)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (
                        session_id, user_id, tool_name,
                        json.dumps(params, ensure_ascii=False),
                        str(result)[:65535] if result else None,
                        error[:65535] if error else None
                    ))
            return True
        except Exception as e:
            logger.error(f"记录工具调用日志失败: {e}")
            return False