from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.logging.config import setup_logging
from app.api.upload import router as upload_router
from app.api.analysis import router as analysis_router
from app.api.review import router as review_router
from app.api.deadlines import router as deadlines_router
from app.api.versions import router as versions_router
from app.api.contracts import router as contracts_router

# Setup logging
setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload_router)
app.include_router(analysis_router)
app.include_router(review_router)
app.include_router(deadlines_router)
app.include_router(versions_router)
app.include_router(contracts_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.APP_VERSION}


@app.get("/")
async def root():
    return {
        "message": "Contract Obligation Assistant API",
        "version": settings.APP_VERSION
    }
