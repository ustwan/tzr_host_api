from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from .adapters.http_father_client import HttpFatherClient
from .usecases.get_server_status import GetServerStatusUseCase

app = FastAPI(title="API_1 server_status")

# CORS middleware для Swagger UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version="1.0.0",
        routes=app.routes,
    )
    # Убираем префикс для прямого доступа через localhost:8081
    openapi_schema["servers"] = [{"url": "/"}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore

uc = GetServerStatusUseCase(HttpFatherClient())


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/server/status")
async def server_status():
    try:
        return await uc.execute()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"api_father error: {e}")
