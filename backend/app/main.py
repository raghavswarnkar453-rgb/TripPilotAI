from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import health, trips
from app.core.config import get_settings
from app.services.errors import PlannerError

settings = get_settings()

app = FastAPI(title=settings.app_name, version=settings.app_version)

# CORS only for the explicitly configured frontend origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(PlannerError)
async def planner_error_handler(_: Request, exc: PlannerError) -> JSONResponse:
    # PlannerError messages are written to be safe to show to users.
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


app.include_router(health.router)
app.include_router(trips.router)
