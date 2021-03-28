from fastapi import APIRouter, Depends, FastAPI
from newhorizons.routers import api

app = FastAPI()

app.include_router(
    api.router,
    prefix='/api/v1')
