"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app import __version__
from app.api import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

configure_logging()
log = get_logger(__name__)
settings = get_settings()

app = FastAPI(
    title="Loan Portfolio Analytics",
    version=__version__,
    description=(
        "Credit union loan portfolio analytics — CECL allowance, ALM rate-shock "
        "simulation, and KPI reporting. Reference implementation."
    ),
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.on_event("startup")
async def on_startup() -> None:
    log.info("service.startup", version=__version__)
