import os
from dotenv import load_dotenv
from dashscope import Generation

#加载环境变量
load_dotenv()
api_key = os.getenv ("DASHSCOPE_API_KEY") or ""

#调用API
# response = Generation.call(
#     model ="qwen-plus",
#     prompt="你好，我是白泽，正在学习通义千问的API调用。",
#     api_key = api_key
# )

# #打印结果
# print("原始输出")
# print(response)

# print("提取输出")

# if response.status_code == 200:
#     print(response.output.text)
# else:
#     print(f"请求失败，状态码:{response.status_code}")
#     print(response.message)


temperatures = [0.0, 0.3, 0.7, 1.0]
prompt="给我一个关于人工智能的创意标题"

for temp in temperatures:
    print(f"\n================= { temp } ========================")
    gen = Generation.call(
        model='qwen-plus',
        prompt=prompt,
        api_key=api_key,
        temperature=temp
    )
    print(gen.output.text)
