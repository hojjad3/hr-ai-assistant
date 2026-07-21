from typing import Literal
from pydantic import BaseModel
from nicegui import ui, app
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage
from app.agent import build_graph
from app.gui import setup_gui
from dotenv import load_dotenv
import os
import uuid
import sqlite3
load_dotenv()
if not os.environ.get('GROQ_API_KEY'):
    raise RuntimeError('CRITICAL: GROQ_API_KEY is not set in the environment or .env file.')

class AskRequest(BaseModel):
    employee_id: str
    question: str
    session_id: str | None = None

class AskResponse(BaseModel):
    answer: str
    source: Literal['rag', 'structured_data', 'unknown']

class HistoryItem(BaseModel):
    role: str
    text: str
    source: str | None = None

class HistoryResponse(BaseModel):
    messages: list[HistoryItem]

class SessionItem(BaseModel):
    session_id: str
    title: str
    created_at: str

class SessionsResponse(BaseModel):
    sessions: list[SessionItem]
graph = build_graph()
_SESSIONS_DB_PATH = os.path.join('data', 'chat_history.sqlite')

def _ensure_sessions_table() -> None:
    with sqlite3.connect(_SESSIONS_DB_PATH) as conn:
        conn.execute('\n            CREATE TABLE IF NOT EXISTS user_sessions (\n                session_id TEXT PRIMARY KEY,\n                employee_id TEXT,\n                title TEXT,\n                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n            )\n        ')
_ensure_sessions_table()
