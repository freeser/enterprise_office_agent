"""
Streamlit 可视化界面
提供友好的操作界面，展示Agent执行过程
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from typing import List, Dict, Any
import uuid
import json

from agent_core import OfficeAgent
from tools import (
    DataAnalyzerTool,
    DocumentGeneratorTool,
    APITool,
    KnowledgeQATool
)

# 页面配置
st.set_page_config(
    page_title="企业智能办公助手",
    page_icon="🤖",
    layout="wide"
)

# ========== 向量存储缓存 ==========
from knowledge import VectorStoreManager

@st.cache_resource
def get_vector_store():
    """缓存向量存储实例，避免重复加载模型和数据库"""
    return VectorStoreManager()

# 初始化Agent（使用缓存避免重复初始化）
@st.cache_resource
def init_agent() -> OfficeAgent:
    agent = OfficeAgent()
    agent.register_tools([
        DataAnalyzerTool(),
        DocumentGeneratorTool(),
        APITool(),
        KnowledgeQATool()
    ])
    return agent

agent = init_agent()

# 会话状态初始化
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "user_id" not in st.session_state:
    st.session_state.user_id = "user_" + str(uuid.uuid4())[:8]
if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploaded_file_path" not in st.session_state:
    st.session_state.uploaded_file_path = None

# ========== 侧边栏 ==========
with st.sidebar:
    st.title("🤖 办公助手")
    st.markdown("---")
    
    # 会话信息
    st.subheader("会话信息")
    st.text(f"会话ID: {st.session_state.session_id[:8]}...")
    st.text(f"用户ID: {st.session_state.user_id}")
    
    if st.button("🔄 新建会话"):
        agent.clear_session(st.session_state.session_id)
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.uploaded_file_path = None
        st.rerun()
    
    st.markdown("---")
    
    # 功能导航
    st.subheader("功能模块")
    mode = st.radio(
        "选择模式",
        ["💬 智能对话", "🔧 工具测试", "📚 知识库管理", "⚙️ 用户偏好"]
    )
    
    # 切换模式时清除上传文件状态
    if mode != "💬 智能对话":
        st.session_state.uploaded_file_path = None
    
    st.markdown("---")
    st.caption(f"版本: 2.0.0")

# ========== 主界面 ==========
st.title("企业智能办公助手")
st.caption("基于 Agent 的智能办公平台 - 数据分析、文档生成、流程审批、知识问答")

if mode == "💬 智能对话":
    # 显示历史消息（Markdown 格式）
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    # 输入框（支持文件上传）
    prompt = st.chat_input(
        "请输入您的指令...",
        accept_file=True,
        file_type=["xlsx", "xls", "csv"]
    )
    
    if prompt:
        # 处理文件上传
        if prompt.files:
            upload_dir = "data/uploads"
            os.makedirs(upload_dir, exist_ok=True)
            for file in prompt.files:
                file_path = os.path.join(upload_dir, file.name)
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())
                st.session_state.uploaded_file_path = file_path
                st.success(f"📁 文件已上传: {file.name}")

        prompt_text = prompt.text or ""
        # 构建最终输入（如果有上传文件，自动附加路径）
        final_input = prompt_text
        if st.session_state.uploaded_file_path:
            final_input = f"{prompt_text}，文件路径: {st.session_state.uploaded_file_path}"

        if prompt_text.strip():
            # 添加用户消息
            st.session_state.messages.append({"role": "user", "content": prompt_text})
            with st.chat_message("user"):
                st.markdown(prompt_text)
                if st.session_state.uploaded_file_path:
                    st.caption(f"📎 {os.path.basename(st.session_state.uploaded_file_path)}")

            # 调用 Agent
            with st.chat_message("assistant"):
                with st.spinner("正在思考中..."):
                    result = agent.run(
                        final_input,
                        st.session_state.session_id,
                        st.session_state.user_id
                    )
                
                # ---- 实时展示区域 ----
                output_text = result.get("output", "")
                st.markdown("### 📝 执行结果")
                # 结果区域用 Markdown 渲染，支持列表、标题等
                if len(output_text) > 800:
                    with st.expander("📄 完整结果", expanded=False):
                        st.markdown(output_text)
                else:
                    st.markdown(output_text)

                # 执行步骤折叠展示
                if result.get("intermediate_steps"):
                    with st.expander("📋 查看执行步骤", expanded=False):
                        for i, step in enumerate(result["intermediate_steps"], 1):
                            # 兼容元组格式（ReAct）和字典格式（规划器）
                            if isinstance(step, tuple):
                                action, obs = step[0], step[1]
                                tool_name = action.tool
                                tool_input = action.tool_input if hasattr(action, 'tool_input') else {}
                            else:
                                tool_name = step.get("tool", "未知工具")
                                tool_input = step.get("tool_input", {})
                                obs = step.get("observation", "")

                            st.markdown(f"**步骤 {i}：{tool_name}**")
                            if tool_input:
                                st.json(tool_input)
                            obs_str = str(obs)
                            if len(obs_str) > 300:
                                with st.expander("结果详情"):
                                    st.code(obs_str, language="text")
                            else:
                                st.code(obs_str, language="text")
                            st.markdown("---")

                # ---- 历史消息存储（只保留最终结果）----
                history_md = f"### 📝 执行结果\n\n{output_text}"
                st.session_state.messages.append({"role": "assistant", "content": history_md})

elif mode == "🔧 工具测试":
    st.subheader("工具单独测试")
    
    # 工具描述字典（美化版）
    tool_descriptions = {
        "data_analyzer": {
            "name": "📊 数据分析工具",
            "description": "支持读取Excel/CSV数据文件，进行数据清洗、统计分析和可视化展示，可自动生成分析报告文档。",
            "features": ["数据读取", "数据清洗", "统计分析", "可视化图表", "报告生成"]
        },
        "document_generator": {
            "name": "📝 文档生成工具",
            "description": "基于AI智能生成各类办公文档，支持会议纪要、工作总结、业务报告等多种文档类型。",
            "features": ["会议纪要", "工作总结", "业务报告", "AI内容生成"]
        },
        "api_tool": {
            "name": "🔗 API调用工具",
            "description": "对接企业内部系统（OA/CRM），支持审批流程发起、状态查询、用户信息获取等功能。",
            "features": ["流程审批", "状态查询", "OA系统", "CRM系统"]
        },
        "knowledge_qa": {
            "name": "💡 知识问答工具",
            "description": "基于企业知识库进行智能问答，支持查询企业规章制度、产品知识等信息。",
            "features": ["制度查询", "产品知识", "RAG检索", "智能问答"]
        }
    }
    
    tool_names = agent.tool_registry.get_tool_names()
    selected_tool = st.selectbox("选择工具", tool_names, format_func=lambda x: tool_descriptions[x]["name"])
    
    if selected_tool:
        tool_info = tool_descriptions[selected_tool]
        with st.container():
            st.markdown(f"### {tool_info['name']}")
            st.info(tool_info["description"])
            features_str = " | ".join([f"**{f}**" for f in tool_info["features"]])
            st.markdown(f"**功能特性**: {features_str}")
        
        st.divider()
        
        if selected_tool == "data_analyzer":
            tool = agent.tool_registry.get_tool(selected_tool)
            with st.container(border=True):
                st.markdown("#### 🎯 操作参数")
                col1, col2 = st.columns(2)
                with col1:
                    action = st.selectbox("操作类型", ["read_data", "clean_data", "analyze", "visualize", "generate_report"])
                with col2:
                    file_path = st.text_input("文件路径", "data/sales_data.xlsx")
                auto_generate_doc = st.checkbox("📄 自动生成Word报告", value=True)
                
                if st.button("🚀 执行", type="primary"):
                    with st.spinner("正在处理..."):
                        result = tool._run(action=action, file_path=file_path, auto_generate_doc=auto_generate_doc)
                    with st.container(border=True):
                        st.markdown("#### 📋 执行结果")
                        st.text_area("结果内容", result, height=300)
        
        elif selected_tool == "document_generator":
            tool = agent.tool_registry.get_tool(selected_tool)
            with st.container(border=True):
                st.markdown("#### 🎯 文档参数")
                doc_type = st.selectbox("文档类型", [("会议纪要", "meeting_notes"), ("工作总结", "work_summary"), ("分析报告", "report")], format_func=lambda x: x[0])
                doc_type = doc_type[1] if isinstance(doc_type, tuple) else doc_type
                
                title = st.text_input("📝 文档标题")
                context = st.text_area("📋 内容描述（用于AI生成）", height=150, placeholder="请输入会议内容、工作详情等信息，AI将据此生成文档...")
                auto_generate = st.checkbox("✨ 使用AI自动生成内容", value=True)
                
                if st.button("🚀 生成文档", type="primary"):
                    with st.spinner("AI正在生成文档..."):
                        result = tool._run(doc_type=doc_type, title=title, context=context, auto_generate=auto_generate)
                    st.success(result)
        
        elif selected_tool == "api_tool":
            tool = agent.tool_registry.get_tool(selected_tool)
            with st.container(border=True):
                st.markdown("#### 🎯 API参数")
                action = st.selectbox("操作类型", [
                    ("发起审批", "process_approval"),
                    ("系统状态", "get_system_status"),
                    ("用户信息", "get_user_info"),
                    ("审批状态", "query_approval_status")
                ], format_func=lambda x: x[0])
                action = action[1] if isinstance(action, tuple) else action
                
                system = st.selectbox("目标系统", ["OA", "CRM"])
                
                if action == "process_approval":
                    approval_type = st.selectbox("审批类型", [
                        ("请假", "leave"), ("报销", "expense"), ("合同", "contract"),
                        ("采购", "purchase"), ("出差", "travel"), ("加班", "overtime")
                    ], format_func=lambda x: x[0])
                    approval_type = approval_type[1] if isinstance(approval_type, tuple) else approval_type
                    use_mock = st.checkbox("🧪 使用模拟模式", value=True)
                
                elif action == "query_approval_status":
                    approval_id = st.text_input("审批单号", "AP20260510001")
                
                elif action == "get_user_info":
                    user_id = st.text_input("用户ID", "001")
                
                btn_label = "🚀 执行" if action == "process_approval" else "🔍 查询"
                if st.button(btn_label, type="primary"):
                    with st.spinner("正在调用API..."):
                        if action == "process_approval":
                            result = tool._run(action=action, system=system, approval_type=approval_type, use_mock=use_mock)
                        elif action == "query_approval_status":
                            result = tool._run(action=action, system=system, approval_id=approval_id)
                        elif action == "get_user_info":
                            result = tool._run(action=action, system=system, user_id=user_id)
                        else:
                            result = tool._run(action=action, system=system)
                    with st.container(border=True):
                        st.markdown("#### 📋 返回结果")
                        st.json(result if isinstance(result, dict) else result)
        
        elif selected_tool == "knowledge_qa":
            tool = agent.tool_registry.get_tool(selected_tool)
            with st.container(border=True):
                st.markdown("#### 🎯 问答参数")
                question = st.text_input("❓ 问题", "公司的年假政策是什么？")
                top_k = st.slider("🔍 检索数量", 1, 10, 4, help="返回最相关的文档片段数量")
                
                if st.button("🚀 提问", type="primary"):
                    with st.spinner("正在检索知识库..."):
                        result = tool._run(question=question, top_k=top_k)
                    with st.container(border=True):
                        st.markdown("#### 📋 回答结果")
                        st.markdown(result)

elif mode == "📚 知识库管理":
    st.subheader("知识库文档管理")
    
    vector_store = get_vector_store()
    count = vector_store.get_document_count()
    st.metric("文档片段总数", count)
    
    # 防止重复上传
    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = set()
    
    uploaded_file = st.file_uploader("上传文档", type=["pdf", "docx", "txt", "xlsx"])
    if uploaded_file and uploaded_file.name not in st.session_state.uploaded_files:
        st.session_state.uploaded_files.add(uploaded_file.name)
        file_path = os.path.join("data/knowledge_base", uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        from knowledge import UniversalDocumentLoader
        loader = UniversalDocumentLoader()
        docs = loader.load_file(file_path)
        if docs:
            vector_store.add_documents(docs)
            st.success(f"成功添加 {len(docs)} 个片段！")
        else:
            st.error("文档解析失败")
            st.session_state.uploaded_files.remove(uploaded_file.name)
    
    if st.button("清空知识库"):
        vector_store.delete_collection()
        st.success("知识库已清空")
        st.session_state.uploaded_files = set()

elif mode == "⚙️ 用户偏好":
    st.subheader("用户偏好设置")
    
    prefs = agent.memory_manager.get_all_preferences(st.session_state.user_id)
    st.write("当前偏好配置：")
    st.json(prefs)
    
    with st.form("add_preference"):
        key = st.text_input("偏好名称")
        value = st.text_input("偏好值")
        submitted = st.form_submit_button("保存")
        if submitted and key and value:
            agent.memory_manager.set_preference(st.session_state.user_id, key, value)
            st.success("偏好已保存")
            st.rerun()