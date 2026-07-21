import modal
import os

# Define the container image with our dependencies
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install_from_requirements("requirements.txt")
    .add_local_dir("data", remote_path="/root/data")
    .add_local_dir("app", remote_path="/root/app")
    .add_local_file("main.py", remote_path="/root/main.py")
)

# Define a persistent network volume for dynamic state (DBs)
storage_vol = modal.Volume.from_name("hr-ai-storage", create_if_missing=True)

app = modal.App("hr-ai-assistant", image=image)

# Define the function with the custom image, volume, and secrets
@app.function(
    volumes={"/root/storage": storage_vol},
    secrets=[
        modal.Secret.from_name("groq-secret"),
        modal.Secret.from_name("hr-login-secret")
    ],
    max_containers=1,
)
@modal.asgi_app()
def fastapi_app():
    # Set the storage secret if not defined
    os.environ.setdefault("STORAGE_SECRET", "modal_hr_secret_key")
    
    # Import the FastAPI app from main.py  
    from main import app as fastapi
    import socketio
    from nicegui import core
    
    # Wrap with Socket.IO so NiceGUI's WebSocket connections work on Modal
    return socketio.ASGIApp(core.sio, fastapi, socketio_path='/socket.io')
