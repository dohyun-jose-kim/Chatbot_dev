"""Streamlit 진입점 — Fishery Byproduct RAG Chatbot.

references/conversational-rag-chatbot app/streamlit_app.py 차용.
FastAPI(05_api, :8000)를 HTTP로 호출하는 얇은 클라이언트.

실행: streamlit run 06_ui/streamlit_app.py  (FastAPI가 먼저 떠 있어야 함)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st
from sidebar import display_sidebar
from chat_interface import display_chat_interface

st.title("Fishery Byproduct Bioactivity — RAG Chatbot")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "model" not in st.session_state:
    st.session_state.model = "gemma3:4b"

display_sidebar()
display_chat_interface()
