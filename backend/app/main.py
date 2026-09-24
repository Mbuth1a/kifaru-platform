from fastapi import FastAPI

app = FastAPI(
    title="Farsi HR & Payroll Intelligence Platform",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "kifaru-api",
        "version": "0.1.0",
    }