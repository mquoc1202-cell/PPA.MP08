from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from src.core.config import settings
from src.core.logging import setup_logging, get_logger
import src.models
from src.core.database import Base, engine, SessionLocal
from src.core.seed import seed_initial_data
from src.core.exceptions import register_exception_handlers
from src.api.v1.api_router import api_router
from src.web.dashboard import router as dashboard_router
from src.web.admin_trucks import router as admin_trucks_router
from src.web.admin_drivers import router as admin_drivers_router
from src.web.auth import router as web_auth_router
from src.web.trips import router as web_trips_router
from src.web.schedule import router as web_schedule_router

# Setup centralized logging
setup_logging(settings.LOG_LEVEL)
logger = get_logger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    
    # Auto-migrate SQLite schema if columns were added to models
    with engine.connect() as conn:
        try:
            cursor = conn.exec_driver_sql("PRAGMA table_info(resource_bookings)")
            columns = [row[1] for row in cursor.fetchall()]
            if columns and "service_type" not in columns:
                logger.info("Migrating resource_bookings: adding service_type column...")
                conn.exec_driver_sql("ALTER TABLE resource_bookings ADD COLUMN service_type VARCHAR(20) NOT NULL DEFAULT 'FREIGHT'")
                conn.commit()

            # Auto-migrate trips table with TRN-03 tracking columns
            cursor = conn.exec_driver_sql("PRAGMA table_info(trips)")
            trip_cols = [row[1] for row in cursor.fetchall()]
            new_trip_cols = [
                ("actual_cargo_weight_kg", "INTEGER"),
                ("handover_person", "VARCHAR(100)"),
                ("cargo_condition", "VARCHAR(255)"),
                ("discrepancy_notes", "VARCHAR(500)"),
                ("actual_pickup_time", "DATETIME"),
                ("actual_depart_time", "DATETIME"),
                ("pickup_recorded_at", "DATETIME"),
                ("depart_recorded_at", "DATETIME"),
                ("actual_delivery_time", "DATETIME"),
                ("actual_completed_time", "DATETIME"),
                ("recipient_name", "VARCHAR(100)"),
                ("delivery_notes", "VARCHAR(500)"),
                ("delivery_recorded_at", "DATETIME"),
                ("completed_recorded_at", "DATETIME"),
            ]
            for col_name, col_type in new_trip_cols:
                if trip_cols and col_name not in trip_cols:
                    logger.info("Migrating trips: adding %s column...", col_name)
                    conn.exec_driver_sql(f"ALTER TABLE trips ADD COLUMN {col_name} {col_type}")
                    conn.commit()
            # Auto-migrate trip_issues table with TRN-05 columns
            cursor = conn.exec_driver_sql("PRAGMA table_info(trip_issues)")
            issue_cols = [row[1] for row in cursor.fetchall()]
            new_issue_cols = [
                ("occurred_at", "DATETIME"),
                ("handled_by", "VARCHAR(150)"),
                ("estimated_resolution_time", "DATETIME"),
                ("resolution_notes", "VARCHAR(1000)"),
                ("resolved_at", "DATETIME"),
            ]
            for col_name, col_type in new_issue_cols:
                if issue_cols and col_name not in issue_cols:
                    logger.info("Migrating trip_issues: adding %s column...", col_name)
                    conn.exec_driver_sql(f"ALTER TABLE trip_issues ADD COLUMN {col_name} {col_type}")
                    conn.commit()
        except Exception as e:
            logger.warning("Auto-migration check skipped: %s", e)
            
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

# Session Middleware with secure signed cookies
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie=settings.SESSION_COOKIE_NAME,
    max_age=settings.SESSION_MAX_AGE,
    same_site="lax",
    https_only=False,
)

# Mount Static assets (CSS, JS, images, design tokens)
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# Include REST API Routers (/api/v1/trucks, /api/v1/drivers)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Include SSR Admin Web Routers (/dashboard, /admin/trucks, /admin/drivers, /login, /logout, /trips, /schedule)
app.include_router(web_auth_router)
app.include_router(dashboard_router)
app.include_router(admin_trucks_router)
app.include_router(admin_drivers_router)
app.include_router(web_trips_router)
app.include_router(web_schedule_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
