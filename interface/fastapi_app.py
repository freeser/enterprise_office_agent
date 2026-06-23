"""
FastAPI 接口服务
提供RESTful API供企业内部系统调用
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn
import logging

from agent_core import OfficeAgent
from tools import (
    DataAnalyzerTool,
    DocumentGeneratorTool,
    APITool,
    KnowledgeQATool
)
from config.settings import settings

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="企业智能办公助手API，支持任务规划、工具调用、知识问答等功能"
)

# 初始化Agent并注册工具
agent = OfficeAgent()
agent.register_tools([
    DataAnalyzerTool(),
    DocumentGeneratorTool(),
    APITool(),
    KnowledgeQATool()
])

# ========== 请求/响应模型 ==========
class TaskRequest(BaseModel):
    user_input: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None

class TaskResponse(BaseModel):
    output: str
    session_id: str
    intermediate_steps: Optional[List] = []

class MemoryResponse(BaseModel):
    history: List[Dict[str, Any]]

class PreferenceRequest(BaseModel):
    key: str
    value: str

class KnowledgeRequest(BaseModel):
    question: str

class ClearMemoryResponse(BaseModel):
    message: str

# ========== API 路由 ==========

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": settings.APP_NAME}

@app.post("/api/chat", response_model=TaskResponse)
async def chat(request: TaskRequest):
    """处理用户对话请求"""
    try:
        result = agent.run(
            user_input=request.user_input,
            session_id=request.session_id,
            user_id=request.user_id
        )
        return TaskResponse(
            output=result["output"],
            session_id=result["session_id"],
            intermediate_steps=result.get("intermediate_steps", [])
        )
    except Exception as e:
        logger.error(f"处理请求失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/memory/{session_id}")
async def get_memory(session_id: str):
    """获取会话记忆"""
    try:
        history = agent.memory_manager.get_messages(session_id)
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/memory/{session_id}/clear")
async def clear_memory(session_id: str):
    """清除会话记忆"""
    try:
        agent.clear_session(session_id)
        return ClearMemoryResponse(message=f"会话 {session_id} 记忆已清除")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/user/{user_id}/preferences")
async def get_user_preferences(user_id: str):
    """获取用户偏好"""
    try:
        prefs = agent.memory_manager.get_all_preferences(user_id)
        return {"preferences": prefs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/user/{user_id}/preferences")
async def set_user_preference(user_id: str, req: PreferenceRequest):
    """设置用户偏好"""
    try:
        success = agent.memory_manager.set_preference(user_id, req.key, req.value)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/knowledge/qa")
async def knowledge_qa(req: KnowledgeRequest):
    """独立知识问答接口（绕过Agent直接调用工具）"""
    tool = KnowledgeQATool()
    answer = tool._run(question=req.question)
    return {"answer": answer}

@app.post("/api/knowledge/upload")
async def upload_document(file: UploadFile = File(...)):
    """上传文档到知识库"""
    try:
        # 保存临时文件
        file_path = os.path.join(settings.KNOWLEDGE_BASE_DIR, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 加载文档并添加到向量库
        from knowledge import UniversalDocumentLoader, VectorStoreManager
        loader = UniversalDocumentLoader()
        docs = loader.load_file(file_path)
        
        if docs:
            vector_store = VectorStoreManager()
            vector_store.add_documents(docs)
            return {"message": f"成功添加文档 {file.filename}，共 {len(docs)} 个片段"}
        else:
            return {"message": "文档加载失败或无内容"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tools")
async def list_tools():
    """列出所有可用工具"""
    tools = agent.tool_registry.list_tools()
    return {"tools": [{"name": t.name, "description": t.description} for t in tools]}

# ========== 模拟OA/CRM回调接口 ==========
@app.post("/api/callback/oa/approval")
async def oa_approval_callback(data: Dict[str, Any]):
    """OA审批回调（模拟）"""
    logger.info(f"收到OA审批回调: {data}")
    return {"status": "received"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)