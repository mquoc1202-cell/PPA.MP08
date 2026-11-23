from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.core.config import settings
from src.core.logging import setup_logging, get_logger
from src.core.database import Base, engine, SessionLocal
from src.core.seed import seed_initial_data
from src.core.exceptions import register_exception_handlers
from src.api.v1.api_router import api_router
from src.web.dashboard import router as dashboard_router
from src.web.admin_trucks import router as admin_trucks_router
from src.web.admin_drivers import router as admin_drivers_router

# Setup centralized logging
setup_logging(settings.LOG_LEVEL)
logger = get_logger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully.")
    
    # Auto-seed initial demo data if database is empty
    with SessionLocal() as db:
        seed_initial_data(db)
        
    yield
    logger.info("Application shutting down...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Hệ thống Quản lý Vận tải Hàng hóa - Module TRN-01 Quản lý xe và tài xế",
    version="1.0.0",
    lifespan=lifespan
)

# Register central error masking & exception handling
register_exception_handlers(app)

# Include REST API Routers (/api/v1/trucks, /api/v1/drivers)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Include SSR Admin Web Routers (/dashboard, /admin/trucks, /admin/drivers)
app.include_router(dashboard_router)
app.include_router(admin_trucks_router)
app.include_router(admin_drivers_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
