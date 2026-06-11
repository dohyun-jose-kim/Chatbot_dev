"""사이드바 — 모델 선택 + 새 세션.

references/conversational-rag-chatbot app/sidebar.py 차용.
문서 업로드/목록/삭제 제거, 모델을 gemma로, '새 세션' 버튼 추가.
"""
import uuid
import streamlit as st


def display_sidebar():
    st.sidebar.selectbox("Model", options=["gemma4:26b", "gemma4:31b"], key="model")
    st.sidebar.caption("gemma4:26b 빠름(개발) · gemma4:31b 고품질(턴당 느림)")

    if st.sidebar.button("새 세션"):
        st.session_state.session_id = None
        st.session_state.messages = []
        st.rerun()

    if st.session_state.get("session_id"):
        st.sidebar.caption(f"session: {st.session_state.session_id[:8]}")
