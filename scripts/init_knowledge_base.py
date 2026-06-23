#!/usr/bin/env python3
"""
初始化知识库脚本
用于批量导入示例文档，演示RAG效果
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge import UniversalDocumentLoader, VectorStoreManager
from config.settings import settings

# 创建示例文档
def create_sample_docs():
    """生成示例企业知识文档"""
    docs_dir = settings.KNOWLEDGE_BASE_DIR
    os.makedirs(docs_dir, exist_ok=True)
    
    # 规章制度文档
    policy_content = """# 企业规章制度

## 考勤制度
- 工作时间为周一至周五 9:00-18:00，午休12:00-13:00
- 员工每日需通过OA系统打卡签到/签退
- 迟到30分钟内扣除当日工资的10%，超过30分钟按旷工半天处理

## 年假政策
- 入职满1年的员工享有每年10天带薪年假
- 入职满5年的员工享有每年15天带薪年假
- 年假可分段使用，但每次请假不少于半天
- 年假需提前3个工作日在OA系统申请

## 报销规定
- 因公产生的交通费、餐饮费可报销，需提供正规发票
- 单笔金额超过500元需提前申请
- 报销流程：OA提交申请 -> 部门负责人审批 -> 财务审核 -> 打款
"""
    policy_path = os.path.join(docs_dir, "company_policy.txt")
    with open(policy_path, "w", encoding="utf-8") as f:
        f.write(policy_content)
    
    # 产品知识文档
    product_content = """# 智能办公助手产品介绍

## 核心功能
1. **数据分析助手**：支持Excel/CSV数据读取、清洗、统计分析和可视化
2. **文档智能生成**：一键生成会议纪要、工作总结、业务报告
3. **流程自动化**：对接OA/CRM系统，自动发起审批流程
4. **知识问答**：基于企业知识库的智能问答，支持规章制度查询

## 技术架构
- 基于LangChain Agent框架
- 接入通义千问大语言模型
- 向量数据库使用Chroma，支持RAG检索增强
- 前后端分离：FastAPI + Streamlit

## 使用场景
- 销售团队：快速生成销售数据分析报告
- 行政部门：智能办理请假、报销审批
- 新员工：自助查询企业规章制度
"""
    product_path = os.path.join(docs_dir, "product_intro.txt")
    with open(product_path, "w", encoding="utf-8") as f:
        f.write(product_content)
    
    print(f"示例文档已创建在 {docs_dir}")

def main():
    print("初始化知识库...")
    
    # 创建示例文档
    create_sample_docs()
    
    # 加载并导入
    loader = UniversalDocumentLoader()
    vector_store = VectorStoreManager()
    
    # 清空旧数据（可选）
    # vector_store.delete_collection()
    # vector_store = VectorStoreManager()  # 重新创建
    
    docs_dir = settings.KNOWLEDGE_BASE_DIR
    all_docs = []
    for filename in os.listdir(docs_dir):
        if filename.endswith(('.txt', '.pdf', '.docx', '.xlsx')):
            file_path = os.path.join(docs_dir, filename)
            print(f"加载文档: {filename}")
            docs = loader.load_file(file_path)
            all_docs.extend(docs)
            print(f"  - 提取 {len(docs)} 个片段")
    
    if all_docs:
        vector_store.add_documents(all_docs)
        print(f"知识库初始化完成，共导入 {len(all_docs)} 个片段")
    else:
        print("没有找到任何文档")

if __name__ == "__main__":
    main()