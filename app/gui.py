from nicegui import ui, app
import httpx
import pandas as pd
import os
from fastapi.responses import RedirectResponse

from fastapi import Request

def setup_gui() -> None:

    def inject_styles() -> None:
        ui.add_head_html("\n        <style>\n        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');\n        body { font-family: 'Outfit', sans-serif; background: radial-gradient(circle at top right, #1e1b4b 0%, #0f172a 100%); color: #f8fafc; margin: 0; min-height: 100vh; }\n        .glass-header { background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(12px); border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding: 20px; position: sticky; top: 0; z-index: 50; }\n        .chat-bubble-user { background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%); color: white; border-radius: 20px 20px 0 20px; padding: 16px 20px; align-self: flex-end; max-width: 80%; box-shadow: 0 4px 20px rgba(59, 130, 246, 0.3); animation: slideInRight 0.4s cubic-bezier(0.16, 1, 0.3, 1); }\n        .chat-bubble-agent { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1); color: #e2e8f0; border-radius: 20px 20px 20px 0; padding: 16px 20px; align-self: flex-start; max-width: 80%; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2); animation: slideInLeft 0.4s cubic-bezier(0.16, 1, 0.3, 1); }\n        .source-badge { background: rgba(0, 0, 0, 0.4); color: #818cf8; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; margin-top: 12px; display: inline-flex; align-items: center; gap: 6px; }\n        .input-panel { background: rgba(15, 23, 42, 0.8); backdrop-filter: blur(12px); border-top: 1px solid rgba(255, 255, 255, 0.05); padding: 24px; position: sticky; bottom: 0; }\n        .custom-btn { background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%) !important; border-radius: 12px !important; color: white !important; font-weight: 600 !important; text-transform: none !important; font-size: 1rem !important; padding: 8px 24px !important; transition: transform 0.2s ease !important; }\n        .custom-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(139, 92, 246, 0.4) !important; }\n        .login-card { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 24px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3); padding: 40px; width: 100%; max-width: 400px; animation: fadeIn 0.5s ease-out; }\n        @keyframes slideInRight { from { opacity: 0; transform: translateX(30px) scale(0.95); } to { opacity: 1; transform: translateX(0) scale(1); } }\n        @keyframes slideInLeft { from { opacity: 0; transform: translateX(-30px) scale(0.95); } to { opacity: 1; transform: translateX(0) scale(1); } }\n        @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }\n        .chat-container-wrapper { scrollbar-width: thin; scrollbar-color: rgba(255,255,255,0.2) transparent; }\n        .glass-drawer { background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(16px); border-right: 1px solid rgba(255, 255, 255, 0.05); }\n        </style>\n        ")

    @ui.page('/login', dark=True)
    def login_page(request: Request):
        inject_styles()
        
        if request.session.get('authenticated'):
            return RedirectResponse('/')
            
        with ui.column().classes('w-full min-h-screen items-center justify-center p-4'):
            with ui.column().classes('login-card items-center gap-6'):
                ui.icon('psychology', size='4rem', color='#818cf8')
                ui.markdown('### HR Assistant Login').classes('m-0 p-0 font-bold tracking-tight text-white')
                
                # Pure HTML form - browser handles submission natively.
                # No JS, no WebSocket, no NiceGUI button magic. Just standard form POST.
                ui.html('''
<form method="POST" action="/api/login" autocomplete="off" style="width: 100%; display: flex; flex-direction: column; gap: 16px;">
    <input name="employee_id" type="text" placeholder="Employee ID (e.g. EMP001)" required
           style="width: 100%; padding: 14px 16px; border-radius: 10px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.2); color: white; font-size: 1rem; outline: none; box-sizing: border-box; font-family: inherit;">
    <input name="password" type="password" placeholder="Password" required
           style="width: 100%; padding: 14px 16px; border-radius: 10px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.2); color: white; font-size: 1rem; outline: none; box-sizing: border-box; font-family: inherit;">
    <button type="submit"
            style="width: 100%; padding: 14px; border: none; border-radius: 12px; background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%); color: white; font-weight: 600; font-size: 1rem; cursor: pointer; font-family: inherit; margin-top: 8px;">
        Sign In
    </button>
</form>
''')

    @ui.page('/', dark=True)
    async def chat_page(request: Request):
        inject_styles()
        
        # Read standard SessionMiddleware keys
        if not request.session.get('authenticated'):
            return RedirectResponse('/login')
            
        import uuid
        if not request.session.get('session_id'):
            request.session['session_id'] = str(uuid.uuid4())
            
        employee_id = request.session.get('employee_id')
        session_id = request.session.get('session_id')
        employee_name = request.session.get('employee_name')
        
        if not employee_name:
            df = pd.read_csv(os.path.join('data', 'employees.csv'))
            match = df.loc[df['employee_id'] == employee_id, 'full_name']
            employee_name = match.iloc[0] if not match.empty else employee_id
            request.session['employee_name'] = employee_name
            
        with ui.left_drawer(value=True).classes('glass-drawer text-white p-4') as drawer:
            
            # Use ui.link styled as a button for robust HTTP GET navigation
            ui.link('New Chat', '/api/new_chat').classes('w-full mb-6 rounded-xl custom-btn shadow-lg text-center block no-underline text-white font-semibold py-2')
            
            ui.markdown('### Previous Chats').classes('mb-2 ml-2 tracking-tight')

            async def load_sessions() -> None:
                try:
                    from main import get_sessions
                    from nicegui import run
                    resp = await run.io_bound(get_sessions, employee_id)
                    sessions = resp.sessions
                    if not sessions:
                        ui.label('No previous chats found.').classes('text-gray-400 italic ml-2 mt-4')
                    for s in sessions:
                        is_current = s.session_id == session_id
                        btn_class = 'w-full text-left truncate justify-start rounded bg-white/20 px-4 py-2 block no-underline text-white' if is_current else 'w-full text-left truncate justify-start rounded hover:bg-white/5 px-4 py-2 block no-underline text-white'
                        ui.link(s.title, f'/api/switch_session?sid={s.session_id}').classes(btn_class)
                except Exception:
                    ui.label('Could not load sessions.').classes('text-red-400 italic ml-2')
            ui.timer(0, load_sessions, once=True)
            
        with ui.header().classes('w-full items-center justify-between glass-header flex flex-row'):
            with ui.row().classes('items-center gap-4'):
                ui.button(on_click=drawer.toggle, icon='menu').props('flat color="white"').classes('mr-2')
                ui.icon('psychology', size='2rem', color='#818cf8')
                ui.markdown('### HR AI Assistant').classes('m-0 p-0 font-bold tracking-tight text-white')
            with ui.row().classes('items-center gap-4'):
                ui.label(f'{employee_name}').classes('font-semibold text-gray-300')
                
                # Use ui.link styled as a button for robust logout
                ui.link('Logout', '/api/logout').classes('rounded-xl border border-white px-4 py-1 text-white no-underline hover:bg-white/10 transition-colors')
        with ui.column().classes('w-full max-w-4xl mx-auto p-6 flex-grow chat-container-wrapper').style('min-height: 70vh; margin-bottom: 100px;'):
            chat_container = ui.column().classes('w-full gap-6 flex flex-col')

        def display_message(role: str, text: str, source: str | None=None) -> None:
            with chat_container:
                if role == 'User':
                    with ui.column().classes('chat-bubble-user'):
                        ui.markdown(text).classes('text-base m-0')
                else:
                    with ui.column().classes('chat-bubble-agent'):
                        ui.markdown(text).classes('text-base m-0 text-gray-200')
                        if source:
                            with ui.row().classes('source-badge'):
                                icon_name = 'data_object' if source == 'structured_data' else 'article' if source == 'rag' else 'public'
                                ui.icon(icon_name, size='1rem')
                                ui.label(source.replace('_', ' ').title())
        loaded_history = False
        try:
            from main import get_history
            from nicegui import run
            resp = await run.io_bound(get_history, session_id)
            history = resp.messages
            if history:
                loaded_history = True
                for msg in history:
                    display_message(msg.role, msg.text, msg.source)
        except Exception:
            pass
        if not loaded_history:
            display_message('Agent', f'Welcome back, **{employee_name}**! How can I assist you with HR policies or your data today?')
        with ui.row().classes('w-full input-panel justify-center items-end gap-4'):
            with ui.row().classes('w-full max-w-4xl items-center gap-4 relative'):
                question_input = ui.input(placeholder='Ask anything about HR...').classes('flex-grow text-lg').props('rounded outlined dark bg-color=blue-grey-9').on('keydown.enter', lambda: send_question())

                async def send_question() -> None:
                    question = question_input.value
                    if not question:
                        return
                    display_message('User', str(question))
                    question_input.value = ''
                    loading_label = None
                    try:
                        from main import ask, AskRequest
                        from nicegui import run
                        req = AskRequest(employee_id=employee_id, question=question, session_id=session_id)
                        with chat_container:
                            loading_label = ui.label('Agent is typing...').classes('text-gray-400 italic mt-2 ml-2 animate-pulse')
                        resp = await run.io_bound(ask, req)
                        display_message('Agent', resp.answer, resp.source)
                    except Exception:
                        display_message('System Error', 'Unable to reach the assistant service. Please try again later.')
                    finally:
                        if loading_label:
                            loading_label.delete()
                ui.button('Send', on_click=send_question).classes('custom-btn shadow-lg px-8').props('icon-right="send"')