import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from database import engine
from models import Base
from logger import logger

from routers.auth import router as auth_router
from routers.users import router as users_router
from routers.watchlist import router as watchlist_router
from routers.chat import router as chat_router
from routers.admin import router as admin_router
from routers.conversations import router as conversations_router
from routers.stocks import router as stocks_router


app = FastAPI(
    title="Stock AI API",
    version="0.1.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://192.168.137.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(
    request: Request,
    call_next
):
    start_time = time.perf_counter()

    logger.info(
        "Request started: %s %s",
        request.method,
        request.url.path
    )

    try:
        response = await call_next(request)

    except Exception:
        process_time = time.perf_counter() - start_time

        logger.exception(
            "Unhandled error: %s %s | %.3fs",
            request.method,
            request.url.path,
            process_time
        )

        raise

    process_time = time.perf_counter() - start_time

    logger.info(
        "Request completed: %s %s | status=%s | %.3fs",
        request.method,
        request.url.path,
        response.status_code,
        process_time
    )

    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
):
    details = []

    for error in exc.errors():
        details.append({
            "field": ".".join(
                str(item)
                for item in error["loc"]
            ),
            "message": error["msg"]
        })

    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "details": details
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception
):
    logger.exception(
        "Unhandled exception at %s %s: %s",
        request.method,
        request.url.path,
        exc
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error"
        }
    )


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(watchlist_router)
app.include_router(chat_router)
app.include_router(admin_router)
app.include_router(conversations_router)
app.include_router(stocks_router)


@app.get("/")
def home():
    return {
        "message": "Stock AI backend is running"
    }


@app.get("/health", tags=["System"])
def health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "ok",
            "database": "connected"
        }

    except Exception:
        logger.exception(
            "Health check database connection failed"
        )

        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "database": "disconnected"
            }
        )
