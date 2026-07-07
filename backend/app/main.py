import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.core.security import get_password_hash
from app.models.auth import User
from app.api.v1 import api_router
from app.core.log_module import system_log, user_log

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for the FastAPI application.

    Handles setup (creating the logs directory, database tables, and seeding 
    the default admin user) on startup, and cleanup actions on shutdown.

    Args:
        app: The FastAPI application instance.
    """
    # Create logs directory if it does not exist
    logs_dir = Path(__file__).resolve().parent.parent / "logs"
    os.makedirs(logs_dir, exist_ok=True)

    log = system_log()
    log.info("INFO: System Starting...")

    banner = r"""
   ______                _                                    _____ ____  ____
  / ____/___ ______ ____(_)___  ____  ____ ___  ____ __  __  / ___// __ \/ __ \
 / /   / __ `/ ___/_  // / __ \/ __ \/ __ `__ \/ __ `/ |/_/  \__ \/ /_/ / /_/ /
/ /___/ /_/ / /   / //_/ / / / / /_/ / / / / / / /_/ />  <   ___/ / _, _/ ____/
\____/\__,_/_/   /___/_/_/ /_/\____/_/ /_/ /_/\__,_/_/|_|  /____/_/ |_/_/
"""
    log.opt(colors=True).info(
        f"<green>{banner}</green>\n"
        f"  <cyan>{settings.PROJECT_NAME}</cyan>  |  "
        f"<yellow>API {settings.API_V1_STR}</yellow>  |  <magenta>Ready</magenta>"
    )

    # Create database tables if they do not exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    # Seed default admin user
    async with SessionLocal() as session:
        result = await session.execute(select(User).filter(User.email == settings.ADMIN_EMAIL))
        admin = result.scalar_one_or_none()
        if not admin:
            hashed_pwd = get_password_hash(settings.ADMIN_PASSWORD)
            admin_user = User(
                email=settings.ADMIN_EMAIL,
                hashed_password=hashed_pwd,
                full_name="System Administrator",
                role="admin",
                is_active=True
            )
            session.add(admin_user)
            await session.commit()
            system_log().info(f"Default admin user created ({settings.ADMIN_EMAIL})")
            
    yield
    shutdown_log = system_log()
    shutdown_log.info("INFO: System Stopping...")

    shutdown_banner = r"""
  ____                 _ _
 / ___| ___   ___   __| | |__  _   _  ___
| |  _ / _ \ / _ \ / _` | '_ \| | | |/ _ \
| |_| | (_) | (_) | (_| | |_) | |_| |  __/
 \____|\___/ \___/ \__,_|_.__/ \__, |\___|
                               |___/
"""
    shutdown_log.opt(colors=True).info(
        f"<red>{shutdown_banner}</red>\n"
        f"  <cyan>{settings.PROJECT_NAME}</cyan>  |  "
        f"<red>Shutdown complete</red>"
    )

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS middleware config for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    """Root endpoint of the API.

    Returns:
        dict: A dictionary containing welcome message, documentation URL, and health endpoint.
    """
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "docs_url": "/docs",
        "health": "/health"
    }

@app.get("/health")
def health():
    """Health check endpoint.

    Returns:
        dict: A dictionary containing the health status.
    """
    return {"status": "healthy"}
