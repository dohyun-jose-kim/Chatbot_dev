"""채팅 말풍선 렌더링 + 입력 처리.

references/conversational-rag-chatbot app/chat_interface.py 차용.
get_api_response로 FastAPI 호출, 검색된 PMID를 expander로 표시.
"""
import streamlit as st
from api_utils import get_api_response


def display_chat_interface():
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and message.get("pmids"):
                with st.expander("검색된 PMID"):
                    st.write(", ".join(message["pmids"]))

    if prompt := st.chat_input("질문을 입력하세요 (예: What bioactivities does fish scale collagen have?)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.spinner("Generating response..."):
            response = get_api_response(prompt, st.session_state.session_id, st.session_state.model)

        if response:
            st.session_state.session_id = response["session_id"]
            st.session_state.messages.append({
                "role": "assistant",
                "content": response["answer"],
                "pmids": response.get("pmids", []),
            })
            with st.chat_message("assistant"):
                st.markdown(response["answer"])
                with st.expander("검색된 PMID"):
                    st.write(", ".join(response.get("pmids", [])))
