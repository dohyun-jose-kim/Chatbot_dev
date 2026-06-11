#!/usr/bin/env bash
# FastAPI(05_api, :8000) + Streamlit(06_ui, :8501) 동시 기동.
# 저장소 루트의 .venv를 사용. Ollama가 떠 있어야 함.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
VENV="$HERE/../.venv/bin"

echo "Starting FastAPI on :8000 ..."
"$VENV/python" -m uvicorn main:app --app-dir "$HERE/05_api" --port 8000 --log-level warning &
API_PID=$!
trap 'kill $API_PID 2>/dev/null' EXIT

# API 헬스 대기
for i in $(seq 1 30); do
  curl -s -o /dev/null http://localhost:8000/docs && break
  sleep 1
done

echo "Starting Streamlit on :8501 ..."
"$VENV/python" -m streamlit run "$HERE/06_ui/streamlit_app.py"
