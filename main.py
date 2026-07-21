from typing import Literal
import pandas as pd
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
import os
os.makedirs('storage', exist_ok=True)
_SESSIONS_DB_PATH = os.path.join('storage', 'chat_history.sqlite')

def _ensure_sessions_table() -> None:
    with sqlite3.connect(_SESSIONS_DB_PATH) as conn:
        conn.execute('\n            CREATE TABLE IF NOT EXISTS user_sessions (\n                session_id TEXT PRIMARY KEY,\n                employee_id TEXT,\n                title TEXT,\n                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n            )\n        ')
_ensure_sessions_table()

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse as FastAPIRedirect, HTMLResponse
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.environ.get('STORAGE_SECRET', 'super_secret_key_hr'))

# The @app.post and @app.get decorators will now use the custom FastAPI app automatically

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

@app.get('/login')
def login_page(request: Request, error: str | None = None):
    if request.session.get('authenticated'):
        return FastAPIRedirect('/')
        
    error_msg = ""
    if error == 'invalid_id':
        error_msg = "<div style='background: rgba(239, 68, 68, 0.2); color: #fca5a5; padding: 12px; border-radius: 8px; margin-bottom: 20px; text-align: center;'>Employee ID not found.</div>"
    elif error == 'invalid_password':
        error_msg = "<div style='background: rgba(239, 68, 68, 0.2); color: #fca5a5; padding: 12px; border-radius: 8px; margin-bottom: 20px; text-align: center;'>Incorrect password.</div>"
        
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>HR Assistant Login</title>
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
        body {{ font-family: 'Outfit', sans-serif; background: radial-gradient(circle at top right, #1e1b4b 0%, #0f172a 100%); color: #f8fafc; margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center; }}
        .login-card {{ background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 24px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3); padding: 40px; width: 100%; max-width: 400px; animation: fadeIn 0.5s ease-out; box-sizing: border-box; }}
        .input-group {{ margin-bottom: 20px; }}
        .input-group label {{ display: block; margin-bottom: 8px; color: #cbd5e1; font-weight: 500; font-size: 0.9rem; }}
        .input-group input {{ width: 100%; padding: 12px; background: rgba(0, 0, 0, 0.2); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; color: white; font-family: inherit; font-size: 1rem; box-sizing: border-box; }}
        .input-group input:focus {{ outline: none; border-color: #818cf8; }}
        .custom-btn {{ background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%); border-radius: 12px; color: white; font-weight: 600; text-transform: none; font-size: 1rem; padding: 12px 24px; transition: transform 0.2s ease; width: 100%; border: none; cursor: pointer; font-family: inherit; margin-top: 10px; }}
        .custom-btn:hover {{ transform: translateY(-2px); box-shadow: 0 8px 25px rgba(139, 92, 246, 0.4); }}
        h3 {{ text-align: center; font-size: 1.5rem; margin-top: 0; margin-bottom: 24px; font-weight: 700; }}
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(20px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        </style>
    </head>
    <body>
        <div class="login-card">
            <h3>HR Assistant Login</h3>
            {error_msg}
            <form method="POST" action="/api/login">
                <div class="input-group">
                    <label>Employee ID</label>
                    <input type="text" name="employee_id" placeholder="e.g. EMP001" required>
                </div>
                <div class="input-group">
                    <label>Password</label>
                    <input type="password" name="password" required>
                </div>
                <button type="submit" class="custom-btn">Sign In</button>
            </form>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.post('/api/login')
async def api_login(request: Request):
    """Handle login via HTML POST so FastAPI sets the signed session cookie."""
    form = await request.form()
    emp_id = str(form.get('employee_id', '')).strip()
    pwd = str(form.get('password', '')).strip()
    
    csv_path = os.path.join('data', 'employees.csv')
    df = pd.read_csv(csv_path)
    try:
        employee_row = df.loc[df['employee_id'] == emp_id].iloc[0]
    except IndexError:
        return HTMLResponse(content='<html><head><meta http-equiv="refresh" content="0; url=/login?error=invalid_id" /></head><body>Redirecting...</body></html>')
        
    if pwd != "password123":
        return HTMLResponse(content='<html><head><meta http-equiv="refresh" content="0; url=/login?error=invalid_password" /></head><body>Redirecting...</body></html>')
    
    request.session['authenticated'] = True
    request.session['employee_id'] = emp_id
    request.session['employee_name'] = employee_row['full_name']
    
    # Modal/Serverless proxies often strip Set-Cookie headers on 3xx redirects.
    # Returning a 200 OK with a meta-refresh guarantees the cookie is saved by the browser.
    return HTMLResponse(content='<html><head><meta http-equiv="refresh" content="0; url=/" /></head><body>Redirecting...</body></html>')

@app.get('/api/logout')
async def api_logout(request: Request):
    request.session.clear()
    return HTMLResponse(content='<html><head><meta http-equiv="refresh" content="0; url=/login" /></head><body>Logging out...</body></html>')

@app.get('/api/new_chat')
async def api_new_chat(request: Request):
    import uuid
    request.session['session_id'] = str(uuid.uuid4())
    return HTMLResponse(content='<html><head><meta http-equiv="refresh" content="0; url=/" /></head><body>Starting new chat...</body></html>')

@app.get('/api/switch_session')
async def api_switch_session(request: Request, sid: str):
    request.session['session_id'] = sid
    return HTMLResponse(content='<html><head><meta http-equiv="refresh" content="0; url=/" /></head><body>Switching chat...</body></html>')

@app.get('/history/{session_id}', response_model=HistoryResponse)
def get_history(session_id: str) -> HistoryResponse:
    config = {'configurable': {'thread_id': session_id}}
    state = graph.get_state(config)
    if not state or not state.values:
        return HistoryResponse(messages=[])
    messages = state.values.get('messages', [])
    history = []
    current_source = None
    for msg in messages:
        if isinstance(msg, HumanMessage):
            history.append(HistoryItem(role='User', text=str(msg.content)))
            current_source = None
        elif isinstance(msg, ToolMessage):
            if msg.name == 'query_employee_data_tool':
                current_source = 'structured_data'
            elif msg.name == 'policy_search_tool':
                current_source = 'rag'
        elif isinstance(msg, AIMessage) and msg.content:
            history.append(HistoryItem(role='Agent', text=str(msg.content), source=current_source))
            current_source = None
    return HistoryResponse(messages=history)

@app.get('/sessions/{employee_id}', response_model=SessionsResponse)
def get_sessions(employee_id: str) -> SessionsResponse:
    with sqlite3.connect(_SESSIONS_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT session_id, title, created_at FROM user_sessions WHERE employee_id = ? ORDER BY created_at DESC', (employee_id,))
        sessions = [SessionItem(session_id=row[0], title=row[1], created_at=row[2]) for row in cursor.fetchall()]
    return SessionsResponse(sessions=sessions)

setup_gui()
ui.run_with(app, storage_secret=os.environ.get('STORAGE_SECRET', 'hr_secret_key_change_me'))