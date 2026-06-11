"""FastAPI /chat HTTP 클라이언트.

references/conversational-rag-chatbot app/api_utils.py 차용.
upload/list/delete 함수 제거 (문서 업로드 기능 없음).
"""
import requests
import streamlit as st

API_URL = "http://localhost:8000"


def get_api_response(question, session_id, model):
    data = {"question": question, "model": model}
    if session_id:
        data["session_id"] = session_id
    try:
        # 31b는 턴당 60~70초 → 타임아웃 넉넉히
        response = requests.post(f"{API_URL}/chat", json=data, timeout=300)
        if response.status_code == 200:
            return response.json()
        st.error(f"API request failed ({response.status_code}): {response.text}")
    except Exception as e:
        st.error(f"An error occurred: {e}")
    return None
