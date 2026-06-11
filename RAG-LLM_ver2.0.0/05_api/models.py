"""Pydantic request/response models for the /chat API.

references/conversational-rag-chatbot api/pydantic_models.py 차용.
ModelName을 gemma로 교체, QueryResponse에 pmids 추가, 문서 관련 모델 제거.
"""
from enum import Enum
from pydantic import BaseModel, Field


class ModelName(str, Enum):
    GEMMA4_31B = "gemma4:31b"
    GEMMA3_4B = "gemma3:4b"


class QueryInput(BaseModel):
    question: str
    session_id: str | None = Field(default=None)
    model: ModelName = Field(default=ModelName.GEMMA3_4B)


class QueryResponse(BaseModel):
    answer: str
    session_id: str
    model: ModelName
    pmids: list[str]
