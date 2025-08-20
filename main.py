import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from api.routes import router
from telegram_bot import run_in_background

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_in_background()
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(router)
