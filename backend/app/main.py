"""FastAPI application entry point for FIBO Omni-Director Pro."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import time

from app.config import settings
from app.models.database import init_db
from app.routes.generation import router as generation_router
from app.routes.brand_export_routes import router as brand_export_router
from app.routes.files import router as files_router
from app.routes.assets import router as assets_router
# from app.routes.brand_protection import router as brand_protection_router  # Temporarily disabled

# Setup logging using settings
settings.setup_logging()
logger = logging.getLogger(__name__)

# Rate limiting storage (in production, use Redis)
rate_limit_storage = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.

    Initializes database on startup.
    """
    logger.info("Starting FIBO Omni-Director Pro Backend...")

    # Initialize database
    init_db()
    logger.info("Database initialized")

    yield

    logger.info("Shutting down...")


# Create FastAPI application
app = FastAPI(
    title="FIBO Omni-Director Pro",
    description="Deterministic Visual Production Studio API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Simple rate limiting middleware."""
    if settings.is_production:
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Clean old entries
        rate_limit_storage[client_ip] = [
            timestamp for timestamp in rate_limit_storage.get(client_ip, [])
            if current_time - timestamp < settings.rate_limit_window
        ]
        
        # Check rate limit
        if len(rate_limit_storage.get(client_ip, [])) >= settings.rate_limit_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"}
            )
        
        # Add current request
        if client_ip not in rate_limit_storage:
            rate_limit_storage[client_ip] = []
        rate_limit_storage[client_ip].append(current_time)
    
    response = await call_next(request)
    
    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY" 
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response

# Security middleware
if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure with your actual domains
    )

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Include routers
app.include_router(generation_router)
app.include_router(brand_export_router)
app.include_router(files_router)
app.include_router(assets_router)
# app.include_router(brand_protection_router)  # Temporarily disabled


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "name": "FIBO Omni-Director Pro",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/api/v1/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for production monitoring."""
    try:
        # Test database connection
        from app.models.database import get_db
        db = next(get_db())
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"
    
    # Check if Bria API key is configured
    bria_configured = bool(settings.bria_api_key and settings.bria_api_key != "your_api_key_here")
    
    overall_status = "healthy" if db_status == "healthy" and bria_configured else "degraded"
    
    return {
        "status": overall_status,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "version": "0.1.0",
        "database": db_status,
        "bria_api": "configured" if bria_configured else "not_configured",
        "environment": settings.environment
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
