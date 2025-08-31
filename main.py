import os
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from database import engine, Base, SessionLocal
from settings import settings
from routers import cameras, workstations, frames, events, ws
from models import Camera, Workstation, Frame
import uvicorn

app = FastAPI(title=settings.APP_NAME)
Base.metadata.create_all(bind=engine)

# include routers
app.include_router(cameras.router)
app.include_router(workstations.router)
app.include_router(frames.router)
app.include_router(events.router)
app.include_router(ws.router)

# templates & static (simple UI)
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates')
os.makedirs(TEMPLATES_DIR, exist_ok=True)
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# serve thumbs directory
os.makedirs(settings.THUMBNAILS_DIR, exist_ok=True)
app.mount('/thumbs', StaticFiles(directory=settings.THUMBNAILS_DIR), name='thumbs')

@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    with SessionLocal() as db:
        cams = db.query(Camera).all()
        ws_list = db.query(Workstation).all()
        frames = db.query(Frame).order_by(Frame.captured_at.desc()).limit(50).all()
        return templates.TemplateResponse('index.html', {'request':request, 'cams':cams, 'ws':ws_list, 'frames':frames, 'app_name':settings.APP_NAME})

if __name__ == "__main__":
    # Запуск через python main.py
    uvicorn.run("main:app", host="0.0.0.0", port=8005, reload=True)