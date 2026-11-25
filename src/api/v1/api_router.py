from fastapi import APIRouter
from src.api.v1.trucks import router as trucks_router
from src.api.v1.drivers import router as drivers_router
from src.api.v1.auth import router as auth_router
from src.api.v1.trips import router as trips_router
from src.api.v1.schedule import router as schedule_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(trips_router)
api_router.include_router(schedule_router)
api_router.include_router(trucks_router)
api_router.include_router(drivers_router)
