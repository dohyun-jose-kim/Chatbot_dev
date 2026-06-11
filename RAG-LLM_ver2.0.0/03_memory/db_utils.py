"""Conversation Memory — 세션별 대화기록 SQLite

references/conversational-rag-chatbot의 db_utils.py 차용.
document_store 관련 함수는 제거 (문서 업로드 기능 안 씀).
DB 파일은 이 모듈 옆에 둔다.
"""
import sqlite3
from pathlib import Path

DB_PATH = str(Path(__file__).resolve().parent / "chat_history.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_application_logs():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS application_logs
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     session_id TEXT,
                     user_query TEXT,
                     response TEXT,
                     model TEXT,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.close()


def insert_application_logs(session_id, user_query, response, model):
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO application_logs (session_id, user_query, response, model) VALUES (?, ?, ?, ?)',
        (session_id, user_query, response, model))
    conn.commit()
    conn.close()


def get_chat_history(session_id):
    """LangChain MessagesPlaceholder가 받는 (role, content) 형식으로 반환."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT user_query, response FROM application_logs WHERE session_id = ? ORDER BY created_at',
        (session_id,))
    messages = []
    for row in cursor.fetchall():
        messages.append(("human", row['user_query']))
        messages.append(("ai", row['response']))
    conn.close()
    return messages


# 모듈 로드 시 테이블 보장
create_application_logs()
