# 01. 임베딩 생성 (PubMedBERT)

## PubMedBERT란 무엇인가

PubMedBERT(`microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext`)는 Microsoft Research에서 공개한 의생명 분야 특화 언어 모델이다. 일반적인 BERT가 Wikipedia + BookCorpus로 사전학습된 반면, PubMedBERT는 PubMed 논문 초록과 전문으로만 학습되었다.

### 왜 PubMedBERT를 선택했는가

- **도메인 특화**: 수산부산물 기능성 연구 논문은 의생명 분야 전문 용어(collagen peptide, chitosan, antioxidant activity 등)로 가득하다. 일반 BERT보다 이러한 용어의 의미를 정확히 표현한다.
- **768차원 출력**: 문장/문단 수준의 의미를 768차원 벡터로 압축한다. 이 벡터 간 거리(L2 distance)로 논문 간 의미적 유사도를 계산할 수 있다.
- **무료/로컬 실행**: HuggingFace에서 다운로드하여 로컬에서 실행한다. 임베딩 생성에 API 비용이 들지 않는다.

---

## 임베딩 생성 과정

### 전체 흐름

```
screened.csv (abstract 컬럼)
    |
    v  Tokenization
[CLS] collagen peptides from fish ... [SEP] [PAD] [PAD] ...
    |
    v  Transformer Forward Pass (12 layers)
각 토큰에 대해 768차원 컨텍스트 벡터 생성
    |
    v  Mean Pooling
attention_mask를 고려하여 모든 토큰 벡터의 가중 평균 계산
    |
    v
768차원 문서 벡터 1개
```

### 단계별 설명

1. **Tokenization**: 초록 텍스트를 WordPiece 토큰으로 분할한다. 최대 길이는 512 토큰이며, 초과분은 잘린다(truncation). 짧은 텍스트는 `[PAD]`로 채운다(padding).

2. **Transformer Forward Pass**: 토큰화된 입력이 12개의 Transformer 인코더 레이어를 통과한다. 각 토큰에 대해 주변 문맥을 반영한 768차원 벡터가 생성된다. `torch.no_grad()`로 그래디언트 계산을 끄고 추론만 수행한다.

3. **Mean Pooling**: `[CLS]` 토큰만 사용하는 대신, 모든 토큰 벡터의 평균을 구한다. 이때 `attention_mask`를 적용하여 `[PAD]` 토큰은 평균에서 제외한다. 이 방식이 문장 유사도 비교에 더 안정적인 결과를 준다.

---

## 입출력

| 항목 | 경로 | 설명 |
|------|------|------|
| 입력 | `data/screened.csv` | 5,590편 논문, abstract 컬럼 사용 |
| 출력 | `outputs/01_embedding/embeddings.npy` | numpy 배열, shape: (5590, 768), ~34MB |
| 출력 | `outputs/01_embedding/pmids.csv` | 각 행이 embeddings.npy의 동일 인덱스 논문에 대응 |

---

## 체크포인트 시스템

5,590편을 배치 크기 32로 처리하면 약 175배치가 필요하며, Intel Mac MPS에서 60~90분 소요된다. 중간에 프로세스가 종료되면 처음부터 다시 시작해야 하므로 체크포인트 시스템을 구현했다.

- **저장 주기**: 50배치(약 1,600건)마다 `chunk_NNNN.npy` 파일로 저장
- **저장 위치**: `outputs/01_embedding/checkpoints/`
- **복구 로직**: 재시작 시 체크포인트 디렉토리를 확인하고, 기존 chunk를 로드한 뒤 마지막 체크포인트 이후 배치부터 재개
- **완료 후 정리**: 최종 `embeddings.npy` 저장 후 체크포인트 파일 삭제

```python
# 체크포인트 저장 로직 (50배치마다)
if (done - start_batch) % CHECKPOINT_INTERVAL == 0:
    chunk_arr = np.vstack(current_chunk)
    save_checkpoint(ckpt_dir, chunk_arr, chunk_idx)
```

---

## Shard 지원

대용량 데이터나 메모리 제한 환경에서는 입력 CSV를 분할하여 처리할 수 있다.

```bash
# 전체 처리 (기본)
python 01_embedding/embed.py

# 샤드별 처리
python 01_embedding/embed.py data/screened_1of3.csv
python 01_embedding/embed.py data/screened_2of3.csv
python 01_embedding/embed.py data/screened_3of3.csv
```

샤드 파일명의 접미사(`_1of3`, `_2of3`, `_3of3`)가 자동으로 출력 파일명에 반영된다:
- `embeddings_1of3.npy`, `pmids_1of3.csv`
- `embeddings_2of3.npy`, `pmids_2of3.csv`
- `embeddings_3of3.npy`, `pmids_3of3.csv`

---

## MPS 설정과 메모리 문제

Intel Mac에서 MPS(Metal Performance Shaders) 백엔드를 사용하면 CPU 대비 상당한 속도 향상이 있다. 다만, 기본 MPS 메모리 관리 설정에서 대량 배치 처리 시 메모리 부족 오류가 발생할 수 있다.

```bash
# MPS 메모리 워터마크 해제 (메모리 부족 방지)
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0
```

이 설정은 PyTorch가 MPS에서 메모리 할당 제한을 두지 않도록 한다. `run_all.sh`에 이미 포함되어 있으므로 별도 설정 없이 실행 가능하다.

MPS가 없는 환경에서는 자동으로 CPU로 폴백된다:

```python
device = "mps" if torch.backends.mps.is_available() else "cpu"
```
