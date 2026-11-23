from fastapi import APIRouter
from src.api.v1.trucks import router as trucks_router
from src.api.v1.drivers import router as drivers_router

api_router = APIRouter()
api_router.include_router(trucks_router)
api_router.include_router(drivers_router)
