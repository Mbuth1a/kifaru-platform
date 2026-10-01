from fastapi import FastAPI

from app.organization.routes import router as organization_router
from app.hr.routes import router as hr_router

app = FastAPI(
    title="Kifaru HR & Payroll Intelligence Platform",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "kifaru-api",
        "version": "0.1.0",
    }


app.include_router(organization_router)
app.include_router(hr_router)