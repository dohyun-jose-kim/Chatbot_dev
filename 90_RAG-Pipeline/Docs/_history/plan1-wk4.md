---

# 이 섹터는 AI를 위한 설명이 있는 부분

---

# NLP 고도화 계획 수립

## 흐름 재정립
다시 생각해본 흐름은 다음과 같다.
논문 Abstract → 청크 분할 → 벡터화 → VectorDB → RAG

### 고민1 : Chunking

***청크 크기를 결정한다는 건, LLM에게 얼마만큼의 맥락을 한 번에 읽게 할 것인가를 결정하는 것***

**1. Fixed-size chunking — 글자 수나 토큰 수로 기계적으로 자르는 방식.**

- 예를 들어 "512 토큰마다 자르고, 앞뒤 50 토큰 overlap." 구현이 가장 쉬움

- 대규모 문서(논문 full-text)에는 적합.

- 문장 중간이 잘리면 의미가 깨짐

**2. Sentence-level chunking — 문장 단위로 자르되, N개 문장을 하나의 청크로 묶는 방식.**

- Abstract 같은 짧은 텍스트에는 자연스럽다고 생각중.

- spaCy, NLTK 같은 sentence tokenizer로 분리.

**3. Recursive chunking — 단락 → 문장 → 단어 순으로 계층적으로 시도하면서, 목표 크기에 맞게 분할.**

- 범용적이라 실무 디폴트로 많이 씀.

- LangChain의 RecursiveCharacterTextSplitter가 대표적. 



**4. Semantic chunking — 문장 간 embedding 유사도를 계산해서, 의미가 급변하는 지점(breakpoint)에서 자르는 방식.**

- LangChain의 SemanticChunker나 LlamaIndex의 SemanticSplitterNodeParser가 이 원리를 적용하는 듯.

- 초기 구상하였던 "청크별 의미화" 방향에 가장 가까워 보임.

### 고민 1 방안: Chunking --> metadata 설계
 - 이미 압축된 텍스트라서 세부 문장 세부 단위로 쪼갯을 때의 효용이 적다.
 - 어치피 벡터간 유사도를 판정해서 논문을 고를 것이기 때무에 사전처럼 모든 내용이 가각 들어있을 필요는 없다. 
 - 따라서, Abstract 전체 = 1 청크로  결정한다. 
 
    - 각 Abstract 벡터에 PMID, MeSH terms, 연도, organism, compound명 같은 structured field를 붙여놓기

    - 벡터 유사도 검색 + 메타데이터 필터링을 조합한 hybrid search가 가능
    
    - Abstract를 잘게 쪼개는 것보다 retrieval 품질을 올리는 데 훨씬 효과가 크리라 기대.


## 결정 한 부분들 : 

1. 결정 ①: 검색 단위(retrieval granularity)


청킹 어떻게 할지에 대해서는 여러가지 캐이스를 다 해보는 것으로 하겠다.
<!-- 
RAG에서 질의를 던졌을 때 돌아오는 단위는 가 뭐였으면 좋겠어? 물었을 떄 결국엔 논문 전체가 llm input 으로 들어가야해. 
Abstract 통째로 임베딩, 메타데이터 포함 하고. -->

2. 결정 ②: 데이터 규모

Abstract가 5000-6000 개 수준 생각중. 인지에 따라 전략이 달라져. 수만 개 이상이면 세분화해서 retrieval precision을 높여야 할 수 있고. retrieval precision의 False Positive 를 줄이는 방식으로, LLM Context Window 를 조절 할 수 있다.


3. 결정 ③: Embedding 모델

어떤 모델로 벡터화할 건지. 대표적 선택지는 

    - OpenAI text-embedding-3-small/large
    - 오픈소스로는 all-MiniLM-L6-v2(가볍고 빠름), BGE-large, E5-large-v2,
    - 생의학 도메인 특화된 BiomedBERT, PubMedBERT 계열. -- Microsoft가 BiomedBERT를 학습시키고 Hugging Face에 올려둠. 실상 같은 모델로 추후 확인됨.
    
수산부산물 + bioactive compound 도메인이면 PubMedBERT 기반 임베딩이 도메인 매칭이 더 나을 수 있음.
```py
from transformers import AutoModel
model = AutoModel.from_pretrained("microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext")
```


4. 결정 ④: VectorDB
 - Chroma를 사용 하기로 했습니다.

Chroma(로컬, 프로토타이핑에 좋음), FAISS(Meta, 로컬, 빠름), Pinecone(클라우드 managed), Weaviate, Qdrant 등의 고려 사항이 있었습니다.

## 기타 고려 사항.
지금 수준에선 고려하지 않았지만 임베딩 모델 자체를 Fine-Tuning 해야 할 시점에 아래 링크를 참고할 수 있습니다. **Domain-Specific Fine-Tune**

"https://huggingface.co/blog/nvidia/domain-specific-embedding-finetune" 

이 문서는 Hugging Face 에 Nvidia 가 작성한 문서입니다. 이 문서에서는 범용 임베딩 모델을 도메인 특화 데이터로 Fine-Tuning하는 파이프라인을 다룹니다. LLM을 활용한 합성 학습 데이터 생성(SDG), Hard Negative Mining을 통한 대조 학습, 그리고 평가/배포까지의 전 과정을 포함합니다.