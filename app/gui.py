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
        
        # Check standard SessionMiddleware key
        if request.session.get('authenticated'):
            return RedirectResponse('/')
            
        # Display errors if any
        err = request.query_params.get('error')
        if err == 'empty':
            ui.notify('Please fill all fields', type='warning', position='top')
        elif err == 'notfound':
            ui.notify('Employee ID not found in database', type='negative', position='top')
        elif err == 'badpwd':
            ui.notify('Invalid password', type='negative', position='top')
            
        with ui.column().classes('w-full min-h-screen items-center justify-center p-4'):
            with ui.column().classes('login-card items-center gap-6'):
                ui.icon('psychology', size='4rem', color='#818cf8')
                ui.markdown('### HR Assistant Login').classes('m-0 p-0 font-bold tracking-tight text-white')
                
                # HTML Form for true HTTP POST without WebSocket dependency
                ui.html('''
                    <form id="loginForm" action="/api/login" method="POST" style="width: 100%; display: flex; flex-direction: column; gap: 1rem;">
                        <input type="text" name="employee_id" placeholder="Employee ID (e.g. EMP001)" required
                               style="width: 100%; padding: 0.85rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.2); background: rgba(0,0,0,0.2); color: white; outline: none; font-family: inherit; font-size: 1rem;">
                        <input type="password" name="password" placeholder="Password" required
                               style="width: 100%; padding: 0.85rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.2); background: rgba(0,0,0,0.2); color: white; outline: none; font-family: inherit; font-size: 1rem;">
                        <button type="button" onclick="document.getElementById('loginForm').submit();" style="width: 100%; padding: 0.85rem; border-radius: 12px; border: none; background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%); color: white; font-weight: 600; font-family: inherit; font-size: 1rem; cursor: pointer; margin-top: 0.5rem; transition: transform 0.2s ease;">Sign In</button>
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
            
            # Use raw HTML anchor for robust HTTP GET navigation without WebSockets
            ui.html('''
                <a href="/api/new_chat" style="display: block; width: 100%; margin-bottom: 1.5rem; text-align: center; text-decoration: none;" class="custom-btn shadow-lg">
                    <span class="material-icons" style="vertical-align: middle; margin-right: 8px;">add</span>New Chat
                </a>
            ''')
            
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
                        bg_style = "background: rgba(255,255,255,0.2);" if is_current else ""
                        hover_class = "" if is_current else "hover:bg-white/5"
                        
                        # Use raw HTML anchor for switching sessions
                        ui.html(f'''
                            <a href="/api/switch_session?sid={s.session_id}" 
                               style="display: block; width: 100%; text-align: left; text-decoration: none; color: white; padding: 0.5rem 1rem; border-radius: 4px; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; {bg_style}"
                               class="{hover_class}">
                               {s.title}
                            </a>
                        ''')
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
                
                # Use raw HTML anchor for robust logout
                ui.html('''
                    <a href="/api/logout" style="border: 1px solid white; border-radius: 12px; padding: 4px 16px; color: white; text-decoration: none; transition: background 0.2s;" onmouseover="this.style.background='rgba(255,255,255,0.1)'" onmouseout="this.style.background='transparent'">
                        Logout
                    </a>
                ''')
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