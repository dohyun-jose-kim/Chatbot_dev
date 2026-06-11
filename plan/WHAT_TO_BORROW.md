# 뭘 빌려올 수 있는가

> 원칙: 직접 짜지 않는다. 빌려와서 구현과 평가만 되면 됨.

---

## 공통 발견: 4개 레포 모두 LangChain + Streamlit 사용

| 레포 | 프레임워크 | UI | 벡터DB |
|------|-----------|-----|--------|
| conversational-rag-chatbot | LangChain | Streamlit | ChromaDB |
| Medical-RAG-LLM | LangChain | FastAPI+HTML | Qdrant |
| Medical-Chatbot-LLM-RAG | LangChain | Jupyter | Pinecone |
| DeepSeek-RAG-Chatbot | LangChain | Streamlit | FAISS |

**결론: LangChain을 프레임워크로, Streamlit을 UI로 쓰면 레퍼런스 코드를 최대한 재활용 가능.**

---

## Phase 1에서 가져올 것: 대화 메모리

### From: conversational-rag-chatbot (`api/langchain_utils.py`)

LangChain의 3단 체인 패턴:

```python
# 1. 이전 대화 기반으로 질문을 독립적 질문으로 재작성
history_aware_retriever = create_history_aware_retriever(llm, retriever, contextualize_prompt)

# 2. 검색 결과 + 히스토리로 답변 생성
question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)

# 3. 합체
rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

# 호출
answer = rag_chain.invoke({"input": question, "chat_history": history})
```

### From: conversational-rag-chatbot (`api/db_utils.py`)

대화 저장: SQLite에 session_id별 저장

```python
# 저장
insert_application_logs(session_id, user_query, gpt_response, model)

# 불러오기
chat_history = get_chat_history(session_id)  # [{role, content}, ...]
```

### 더 간단한 대안: DeepSeek-RAG-Chatbot (`app.py`)

Streamlit session_state에 직접 저장 (DB 없이):

```python
st.session_state.messages = []  # [{role, content}, ...]
chat_history = "\n".join([msg["content"] for msg in st.session_state.messages[-5:]])
```

### 추천
- **먼저** DeepSeek 방식 (session_state, 간단) → 동작 확인
- **나중에** conversational-rag 방식 (SQLite, 영구 저장) → 필요 시 전환

---

## Phase 1에서 가져올 것: 스트리밍

### From: DeepSeek-RAG-Chatbot (`app.py`)

Ollama 스트리밍이지만, Claude API `stream=True`로 동일하게 적용 가능:

```python
# 토큰 단위 출력
with st.chat_message("assistant"):
    placeholder = st.empty()
    full_response = ""
    for chunk in response.iter_lines():
        token = json.loads(chunk)["response"]
        full_response += token
        placeholder.markdown(full_response + "▌")
    placeholder.markdown(full_response)
```

---

## Phase 2에서 가져올 것: UI

### From: DeepSeek-RAG-Chatbot + conversational-rag-chatbot

Streamlit 챗봇 UI 패턴:

```python
# 채팅 기록 표시
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 입력
if prompt := st.chat_input("질문하세요"):
    st.session_state.messages.append({"role": "user", "content": prompt})
```

사이드바: 모델 선택, Top-K 조절, 문서 업로드 등

---

## Phase 2에서 가져올 것: Re-ranking

### From: DeepSeek-RAG-Chatbot (`utils/retriever_pipeline.py`)

Cross-encoder 리랭킹:

```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

pairs = [[query, doc.page_content] for doc in docs]
scores = reranker.predict(pairs)
ranked_docs = [doc for _, doc in sorted(zip(scores, docs), reverse=True)]
```

---

## Phase 3에서 가져올 것: Hybrid Search + HyDE

### From: DeepSeek-RAG-Chatbot (`utils/doc_handler.py`)

Hybrid Search (BM25 + 시맨틱):

```python
from langchain.retrievers import EnsembleRetriever, BM25Retriever

ensemble_retriever = EnsembleRetriever(
    retrievers=[bm25_retriever, vector_store.as_retriever()],
    weights=[0.4, 0.6]  # BM25 40%, 시맨틱 60%
)
```

HyDE (가상 답변 생성 후 검색):

```python
def expand_query(query, llm):
    hypothetical = llm.generate(f"Generate a hypothetical answer to: {query}")
    return f"{query}\n{hypothetical}"
```

---

## 평가에서 가져올 것: RAGAS

### From: Medical-Chatbot-LLM-RAG (`MedBot.ipynb`)

```python
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall, answer_correctness
from ragas import evaluate

eval_data = {
    "question": [...],
    "contexts": [[retrieved_docs]],
    "ground_truth": [...],
    "answer": [rag_answers]
}

result = evaluate(dataset=Dataset.from_dict(eval_data), metrics=[...])
```

**측정 가능한 7개 메트릭:**
| 메트릭 | 무엇을 측정 |
|-------|-----------|
| Context Precision | 검색 결과 중 관련 있는 비율 |
| Context Recall | 관련 문서를 얼마나 찾았는지 |
| Faithfulness | 답변이 검색 결과에 근거하는지 |
| Answer Relevancy | 답변이 질문에 맞는지 |
| Answer Correctness | 답변이 정답과 일치하는지 |

---

## 요약: 우리가 직접 짜야 하는 것

거의 없다.

| 조각 | 출처 | 직접 짤 것 |
|------|------|-----------|
| RAG 프레임워크 | LangChain | ❌ |
| 대화 메모리 | LangChain + session_state | ❌ |
| 히스토리 기반 검색 | `create_history_aware_retriever` | ❌ |
| 스트리밍 | Claude API stream + Streamlit | 연결만 |
| UI | Streamlit `chat_input/chat_message` | 레이아웃만 |
| Re-ranking | CrossEncoder (sentence-transformers) | ❌ |
| Hybrid Search | LangChain EnsembleRetriever | ❌ |
| HyDE | LLM 호출 1줄 | 거의 ❌ |
| 평가 | RAGAS 라이브러리 | 테스트 데이터만 |
| 임베딩 | PubMedBERT (기존 것 유지) | ✅ 이미 있음 |
| 벡터DB | ChromaDB (기존 것 유지) | ✅ 이미 있음 |

**직접 짜야 할 것: 각 조각을 연결하는 글루 코드 + 우리 도메인에 맞는 프롬프트 + 평가용 테스트 데이터셋**
