"""채팅 말풍선 렌더링 + 입력 처리 (ver2.6.0).

get_api_response로 FastAPI 호출. 에이전트의 tool 호출(steps)과 검색된 PMID를 expander로 표시.
"""
import streamlit as st
from api_utils import get_api_response


def _render_extras(msg):
    steps = msg.get("steps") or []
    if steps:
        with st.expander("🔧 도구 호출"):
            for s in steps:
                st.write(f"`{s.get('tool', '')}` — {s.get('query', '')}")
    if msg.get("pmids"):
        with st.expander("검색된 PMID"):
            st.write(", ".join(msg["pmids"]))


def display_chat_interface():
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                _render_extras(message)

    if prompt := st.chat_input("질문을 입력하세요 (예: What bioactivities does fish scale collagen have?)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.spinner("Generating response..."):
            response = get_api_response(prompt, st.session_state.session_id, st.session_state.model)

        if response:
            st.session_state.session_id = response["session_id"]
            msg = {
                "role": "assistant",
                "content": response["answer"],
                "pmids": response.get("pmids", []),
                "steps": response.get("steps", []),
            }
            st.session_state.messages.append(msg)
            with st.chat_message("assistant"):
                st.markdown(msg["content"])
                _render_extras(msg)
