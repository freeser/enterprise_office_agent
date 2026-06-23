# 启动后端
uvicorn interface.fastapi_app:app --host 0.0.0.0 --port 8000

# 启动前端
python -m streamlit run interface/streamlit_app.py --server.port 8501