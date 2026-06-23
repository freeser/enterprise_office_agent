# 测试 Agent 的脚本
"""
企业智能办公助手 - 完整功能测试
测试所有核心功能：数据分析、文档生成、API调用、知识问答
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_core import OfficeAgent
from tools import (
    DataAnalyzerTool,
    DocumentGeneratorTool,
    APITool,
    KnowledgeQATool
)
from config.settings import settings


def print_separator(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_data_analysis(agent):
    """测试数据分析功能"""
    print_separator("测试1: 数据分析 + 生成报告")

    result = agent.run(
        "分析销售数据并生成报告",
        use_planner=True
    )

    print(f"输出: {result.get('output', '')[:500]}...")
    print(f"规划模式: {result.get('planned', False)}")
    print(f"步骤数: {result.get('steps_count', 0)}")

    return result


def test_meeting_notes(agent):
    """测试会议纪要生成"""
    print_separator("测试2: 生成会议纪要")

    result = agent.run(
        "生成项目评审会议的会议纪要",
        use_planner=True
    )

    print(f"输出: {result.get('output', '')[:500]}...")
    return result


def test_work_summary(agent):
    """测试工作总结生成"""
    print_separator("测试3: 生成工作总结")

    result = agent.run(
        "生成本月工作总结",
        use_planner=True
    )

    print(f"输出: {result.get('output', '')[:500]}...")
    return result


def test_approval(agent):
    """测试审批流程"""
    print_separator("测试4: 发起请假审批")

    result = agent.run(
        "我想申请年假5天",
        use_planner=True
    )

    print(f"输出: {result.get('output', '')[:500]}...")
    return result


def test_knowledge_qa(agent):
    """测试知识问答"""
    print_separator("测试5: 企业知识问答")

    result = agent.run(
        "公司的年假政策是什么？",
        use_planner=False
    )

    print(f"输出: {result.get('output', '')[:500]}...")
    return result


def test_approval_query(agent):
    """测试审批查询"""
    print_separator("测试6: 查询审批状态")

    result = agent.run(
        "查看OA系统状态",
        use_planner=True
    )

    print(f"输出: {result.get('output', '')[:500]}...")
    return result


def main():
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║     企业智能办公助手 - 功能测试                            ║
    ║     Enterprise Office Assistant - Feature Test            ║
    ╚════════════════════════════════════════════════════════════╝
    """)

    print(f"LLM模型: {settings.LLM_MODEL_NAME}")
    print(f"API Key配置: {'已配置' if settings.DASHSCOPE_API_KEY else '未配置'}")

    if not settings.DASHSCOPE_API_KEY:
        print("\n⚠️ 警告: 未配置 DASHSCOPE_API_KEY，部分功能可能无法正常工作")

    print_separator("初始化 Agent")

    agent = OfficeAgent(enable_planner=True)

    agent.register_tools([
        DataAnalyzerTool(),
        DocumentGeneratorTool(),
        APITool(),
        KnowledgeQATool()
    ])

    print("✅ Agent 初始化成功")
    print(f"✅ 已注册工具: {agent.tool_registry.get_tool_names()}")

    print_separator("开始测试")

    test_functions = [
        ("数据分析+报告生成", test_data_analysis),
        ("会议纪要生成", test_meeting_notes),
        ("工作总结生成", test_work_summary),
        ("请假审批", test_approval),
        ("知识问答", test_knowledge_qa),
        ("系统状态查询", test_approval_query),
    ]

    results = {}
    for name, test_func in test_functions:
        try:
            results[name] = test_func(agent)
        except Exception as e:
            print(f"\n❌ {name} 测试失败: {str(e)}")
            import traceback
            traceback.print_exc()
            results[name] = {"error": str(e)}

    print_separator("测试完成 - 汇总")

    for name, result in results.items():
        status = "✅ 成功" if "error" not in result else "❌ 失败"
        print(f"{status}  {name}")

        if result.get("planned"):
            print(f"     规划模式: 是, 步骤数: {result.get('steps_count', 0)}")

    print("\n" + "=" * 60)
    print("测试全部完成！")
    print("=" * 60)

    return results


if __name__ == "__main__":
    main()
