# 02. 벡터 데이터베이스 (ChromaDB)

## ChromaDB란 무엇인가

ChromaDB는 벡터 임베딩을 저장하고 유사도 검색을 수행하는 오픈소스 벡터 데이터베이스이다. 이 프로젝트에서는 PubMedBERT로 생성한 768차원 임베딩 벡터를 저장하고, 사용자 질문과 가장 유사한 논문을 빠르게 검색하는 데 사용한다.

### 왜 ChromaDB를 선택했는가

- **경량**: 별도 서버 없이 로컬 파일 시스템에 직접 저장/로드 (PersistentClient)
- **Python 네이티브**: pip install로 설치, Python API로 직접 조작
- **메타데이터 지원**: 벡터와 함께 논문의 제목, 연도, 저널, MeSH 용어 등을 저장하여 검색 결과에서 바로 활용 가능
- **자동 인덱싱**: 문서 추가 시 자동으로 유사도 검색용 인덱스 구축

---

## 저장 구조

ChromaDB의 `pubmed_abstracts` 컬렉션에 문서당 다음 4종류의 데이터가 저장된다:

| 항목 | 설명 | 예시 |
|------|------|------|
| **id** | 문서 고유 식별자 (PMID를 문자열로 사용) | `"30047062"` |
| **embedding** | PubMedBERT 768차원 벡터 | `[0.0312, -0.0145, ...]` (768개 float) |
| **document** | 논문 초록 원문 | `"Collagen was extracted from..."` |
| **metadata** | 구조화된 메타 정보 | 아래 표 참조 |

### 메타데이터 필드

| 필드 | 타입 | 설명 | 최대 길이 |
|------|------|------|----------|
| `pmid` | str | PubMed 논문 ID | - |
| `title` | str | 논문 제목 | 500자 |
| `year` | int | 출판 연도 (없으면 0) | - |
| `journal` | str | 저널명 | 200자 |
| `mesh_terms` | str | MeSH 용어 목록 | 500자 |

---

## 빌드 과정

`02_vectordb/build_db.py`가 수행하는 작업:

1. **데이터 로드**: `screened.csv`에서 메타데이터, `embeddings.npy`에서 벡터, `pmids.csv`에서 PMID 매핑을 로드한다.
2. **정합성 검증**: PMID 수와 임베딩 행 수가 일치하는지 assert로 확인한다.
3. **기존 컬렉션 삭제**: 동일 이름의 컬렉션이 있으면 삭제 후 새로 생성한다 (멱등성 보장).
4. **배치 적재**: 500건씩 `collection.add()`로 벡터, 문서, 메타데이터를 동시에 저장한다.
5. **검증 쿼리**: 빌드 완료 후 첫 번째 문서의 임베딩으로 유사 문서 5편을 검색하여 DB가 정상 동작하는지 확인한다.

```
로드: screened.csv + embeddings.npy + pmids.csv
    |
    v  PMID 기반 필터링 및 정렬
    |
    v  배치 500건씩 ChromaDB에 add
    |
    v  검증 쿼리 (첫 번째 문서 기준 Top-5)
    |
    v  완료: 5,590건 저장됨
```

---

## 디렉토리 구조

```
outputs/02_vectordb/
    └── chroma_db/
        ├── chroma.sqlite3        # 메타데이터 + 인덱스
        └── *.bin                 # 벡터 데이터 파일
```

ChromaDB는 `PersistentClient`를 사용하므로, `chroma_db/` 디렉토리가 곧 데이터베이스 전체이다. 이 디렉토리를 삭제하면 DB가 초기화되며, `build_db.py`를 다시 실행하면 재구축된다.

---

## 검증 쿼리

빌드 완료 후 자동 실행되는 검증 쿼리의 출력 예시:

```
-- Verification Query --
  Query: nearest neighbors of PMID=30047062
  [1] PMID: 30047062 (dist: 0.0000)    # 자기 자신 (거리 0)
      Methods for Assessments of Collagenolytic Activity...
  [2] PMID: 29874447 (dist: 4.2351)
      Biologically Active Substances from Marine Hydrobionts...
  [3] PMID: 19351034 (dist: 5.1023)
      The textile materials containing chitosan...
  ...
```

거리(dist)가 0인 결과가 첫 번째로 나오면 벡터 저장이 정상적으로 이루어진 것이다.

---

## 설정값 (config.py)

| 설정 | 값 | 설명 |
|------|---|------|
| `COLLECTION_NAME` | `"pubmed_abstracts"` | ChromaDB 컬렉션 이름 |
| `CHROMA_BATCH_SIZE` | `500` | 한 번에 저장하는 문서 수 |
| `CHROMA_DIR` | `outputs/02_vectordb/chroma_db` | DB 저장 경로 |
