FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY . .

RUN mkdir -p data/knowledge_base data/documents data/visualizations data/chroma_db

EXPOSE 8000
EXPOSE 8501

# 启动命令可根据需要修改
CMD ["sh", "-c", "uvicorn interface.fastapi_app:app --host 0.0.0.0 --port 8000 & streamlit run interface/streamlit_app.py --server.port 8501 --server.address 0.0.0.0"]