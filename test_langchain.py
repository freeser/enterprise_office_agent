import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

#加载环境变量
load_dotenv()
api_key = os.getenv ("DASHSCOPE_API_KEY") or ""

llm = ChatOpenAI(
    model='qwen-plus',
    temperature=0.7,
    max_tokens=2000,
    api_key=api_key,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

response = llm.invoke("解释下什么是LangChain")
print(response.content)