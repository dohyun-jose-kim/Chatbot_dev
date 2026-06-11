"""Multi-turn RAG Chain — ChatOllama + history-aware retriever

references/conversational-rag-chatbot의 langchain_utils.py 구조를 차용:
  create_history_aware_retriever + create_retrieval_chain.
LLM은 ChatOllama로 교체, 논문 포맷은 ver1 CONTEXT_TEMPLATE을 document_prompt로 주입.
LangChain 1.x에서 레거시 체인이 langchain_classic으로 분리됨.
"""
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_classic.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain

from config import LLM_MODEL, SYSTEM_PROMPT, CONTEXT_TEMPLATE
from pubmedbert_retriever import PubMedBERTRetriever

# 후속 질문을 대화기록과 합쳐 standalone 질문으로 재작성 (검색용)
contextualize_q_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "Given a chat history and the latest user question which might reference "
     "context in the chat history, formulate a standalone question which can be "
     "understood without the chat history. Do NOT answer the question, just "
     "reformulate it if needed and otherwise return it as is."),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
])

# 검색된 논문 + 대화기록으로 답변 생성
qa_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("system", "Context:\n{context}"),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
])

# 각 논문 Document를 PMID/연도/저널/제목 포함 형식으로 렌더링
document_prompt = PromptTemplate.from_template(CONTEXT_TEMPLATE)


def get_rag_chain(model: str = LLM_MODEL):
    llm = ChatOllama(model=model)
    retriever = PubMedBERTRetriever()
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_q_prompt
    )
    question_answer_chain = create_stuff_documents_chain(
        llm, qa_prompt, document_prompt=document_prompt
    )
    return create_retrieval_chain(history_aware_retriever, question_answer_chain)
