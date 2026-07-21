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

@app.post('/ask', response_model=AskResponse)
def ask(payload: AskRequest) -> AskResponse:
    thread_id = payload.session_id or str(uuid.uuid4())
    with sqlite3.connect(_SESSIONS_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM user_sessions WHERE session_id = ?', (thread_id,))
        if not cursor.fetchone():
            title = payload.question[:40] + ('...' if len(payload.question) > 40 else '')
            cursor.execute('INSERT INTO user_sessions (session_id, employee_id, title) VALUES (?, ?, ?)', (thread_id, payload.employee_id, title))
            conn.commit()
    config = {'configurable': {'thread_id': thread_id}}
    state = {'messages': [HumanMessage(content=payload.question)], 'employee_id': payload.employee_id}
    result = graph.invoke(state, config=config)
    messages = result['messages']
    last_msg = messages[-1]
    answer = str(last_msg.content)
    tools_called: list[str] = []
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            break
        if isinstance(msg, ToolMessage):
            tools_called.append(msg.name)
    tools_called.reverse()
    source: Literal['rag', 'structured_data', 'unknown'] = 'unknown'
    if tools_called:
        last_tool = tools_called[-1]
        if last_tool == 'query_employee_data_tool':
            source = 'structured_data'
        elif last_tool == 'policy_search_tool':
            source = 'rag'
    if 'i dont know' in answer.lower().replace("'", '').replace('’', ''):
        source = 'unknown'
    return AskResponse(answer=answer, source=source)
