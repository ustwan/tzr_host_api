import os
import re
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from .adapters.http_father_client import HttpFatherClient
from .usecases.register_proxy import RegisterProxyUseCase


API_FATHER_URL = os.getenv("API_FATHER_URL", "http://api_father:9000")


class RegisterRequest(BaseModel):
    login: str
    password: str
    gender: int = Field(..., ge=0, le=1)
    telegram_id: int
    username: str | None = None
    user_created_at: str | None = None
    user_registration_ip: str | None = None
    user_Country: str | None = None
    Request_Id: str | None = Field(None, alias="Request-Id")
    user_registration_type: str | None = None
    
    @field_validator('login')
    @classmethod
    def validate_login(cls, v: str) -> str:
        """
        Валидация логина согласно example/register.py:
        - Английские: буквы + цифры + '_' + '-' + пробел (3-16 символов)
        - Русские: буквы + цифры + '_' + '-' + пробел (3-16 символов, включая ё/Ё)
        """
        # Английский паттерн
        pattern_en = r'^(?=.*[a-zA-Z])[a-zA-Z0-9_\-\ ]{3,16}$'
        # Русский паттерн
        pattern_ru = r'^(?=.*[а-яА-ЯёЁ])[а-яА-ЯёЁ0-9_\-\ ]{3,16}$'
        
        if not (re.fullmatch(pattern_en, v) or re.fullmatch(pattern_ru, v)):
            raise ValueError(
                'Логин должен быть длиной от 3 до 16 символов и '
                'состоять из русских или английских букв, разрешены символы "-", "_", цифры и пробел'
            )
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Валидация пароля: 6-20 ASCII символов"""
        pattern_ascii = r'^[\x20-\x7E]{6,20}$'
        if not re.fullmatch(pattern_ascii, v):
            raise ValueError(
                'Пароль должен быть длиной от 6 до 20 символов и состоять из латиницы'
            )
        return v


app = FastAPI(title="API_2 Register")

# CORS middleware для Swagger UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = request.headers.get("X-Request-Id")
    # Собираем поля с сообщениями как в спецификации
    fields: dict[str, str] = {}
    for err in exc.errors():
        loc = err.get("loc", [])
        if len(loc) >= 2 and loc[0] == "body":
            field = str(loc[1])
            if field == "login":
                fields["login"] = "Ошибка: Логин должен быть от 3 до 16 символов"
            elif field == "password":
                fields["password"] = "Ошибка: Пароль должен быть от 6 до 20 символов на латинице"
            elif field == "gender":
                fields["gender"] = "Ошибка: Вы не выбрали пол персонажа"

    if fields:
        body = {
            "ok": False,
            "error": "validation_error",
            "message": "Ошибка валидации входных данных",
            "fields": fields,
            "request_id": request_id,
        }
        return JSONResponse(status_code=400, content=body)

    # Общая ошибка запроса
    body = {
        "ok": False,
        "error": "bad_request",
        "message": "Ошибка",
        "request_id": request_id,
    }
    return JSONResponse(status_code=400, content=body)

@app.post("/register")
async def register(req: RegisterRequest, request: Request):
    request_id = req.Request_Id or request.headers.get("X-Request-Id")
    payload = req.dict(by_alias=True)
    if request_id:
        payload["Request-Id"] = request_id
    try:
        uc = RegisterProxyUseCase(HttpFatherClient())
        status, content, media_type = await uc.execute(payload)
        return Response(content=content, status_code=status, media_type=media_type)
    except Exception:
        raise HTTPException(status_code=502, detail={
            "ok": False,
            "error": "father_unreachable",
            "message": "Ошибка: на сервере ведутся технические работы. Попробуйте позже",
            "request_id": request_id,
        })


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/register/health")
async def register_health():
    return {"status": "ok"}


