from contextlib import asynccontextmanager
from fastapi import FastAPI
from api.routes import router
from telegram_bot import start_bot, stop_bot

@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_bot()
    try:
        yield
    finally:
        await stop_bot()

app = FastAPI(lifespan=lifespan)
app.include_router(router)
