# 환경 요구사항

## Python 버전

- **Python 3.12.12**

---

## pip 패키지

| 패키지 | 버전 | 용도 |
|--------|------|------|
| `torch` | 2.2.2 | PyTorch, PubMedBERT 모델 추론 (MPS/CPU) |
| `transformers` | 4.45.2 | HuggingFace Transformers, PubMedBERT 로드 |
| `chromadb` | 1.5.5 | 벡터 데이터베이스, 유사도 검색 |
| `anthropic` | 0.89.0 | Claude API SDK |
| `google-genai` | (최신) | Gemini API SDK (선택, 폴백용) |
| `pandas` | (호환 버전) | CSV 데이터 로드 및 처리 |
| `numpy` | (호환 버전) | 임베딩 배열 저장/로드 (.npy) |

### requirements.txt 내용

```
torch>=2.2
transformers>=4.40
chromadb>=1.0
pandas
numpy
anthropic>=0.89
google-genai
```

---

## API 키

| 키 | 필수 여부 | 설명 |
|----|----------|------|
| `ANTHROPIC_API_KEY` | **필수** | Claude API 호출에 필요. https://console.anthropic.com/ 에서 발급 |
| `GEMINI_API_KEY` | 선택 | Gemini 폴백 사용 시 필요. `config.py`에서 `LLM_BACKEND = "gemini"`로 변경 |

API 키 설정 방법:

```bash
# 방법 1: ~/.zshrc에 추가 (영구)
export ANTHROPIC_API_KEY='sk-ant-api03-...'

# 방법 2: 별도 파일로 관리
echo "export ANTHROPIC_API_KEY='sk-ant-api03-...'" > ~/.anthropic_key
source ~/.anthropic_key
```

`run_all.sh`는 `~/.anthropic_key`에서 자동으로 키를 로드한다.

---

## 하드웨어

| 항목 | 테스트 환경 | 최소 요구 |
|------|-----------|----------|
| CPU | Intel Mac | x86_64 또는 Apple Silicon |
| RAM | 16GB | 8GB 이상 권장 |
| 디스크 | SSD | 임베딩 ~34MB + ChromaDB ~100MB + 모델 캐시 ~500MB |
| GPU | MPS (Metal) | 없어도 CPU로 동작 (속도 저하) |

MPS 가속 사용 시 환경변수 설정이 필요하다:
```bash
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0
```

---

## 가상 환경

프로젝트 가상 환경 경로:
```
/Users/inco/01_Projects/00_Tasks/ifc_ojt_dh.kim/.venv/
```

`run_all.sh`에서 이 경로의 Python을 직접 참조한다:
```bash
VENV="/Users/inco/01_Projects/00_Tasks/ifc_ojt_dh.kim/.venv/bin/python"
```

---

## 설치 방법

```bash
# 1. 가상 환경 활성화
source /Users/inco/01_Projects/00_Tasks/ifc_ojt_dh.kim/.venv/bin/activate

# 2. 패키지 설치
pip install -r requirements.txt

# 3. API 키 설정 (아직 안 했다면)
echo "export ANTHROPIC_API_KEY='sk-ant-api03-...'" > ~/.anthropic_key

# 4. PubMedBERT 모델 다운로드 (첫 실행 시 자동, ~500MB)
# 수동으로 미리 다운로드하려면:
python -c "from transformers import AutoModel, AutoTokenizer; AutoModel.from_pretrained('microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext'); AutoTokenizer.from_pretrained('microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext')"

# 5. 연결 테스트
source ~/.anthropic_key
python -c "import anthropic; c = anthropic.Anthropic(); print(c.messages.create(model='claude-haiku-4-5-20251001', max_tokens=10, messages=[{'role':'user','content':'Say OK'}]).content[0].text)"
```
