from fastapi import APIRouter, HTTPException, Request
import logging

from usecases.register_user import RegisterUserUseCase
from schemas import RegisterRequestSchema

logger = logging.getLogger(__name__)


def build_router(register_uc: RegisterUserUseCase) -> APIRouter:
    router = APIRouter()

    @router.post("/internal/register")
    async def internal_register(req: RegisterRequestSchema, request: Request):
        if register_uc is None:
            raise HTTPException(status_code=503, detail="service unavailable")
        try:
            await register_uc.execute(
                login=req.login,
                password=req.password,
                gender=req.gender,
                telegram_id=req.telegram_id,
                username=req.username,
                game_server_host=request.app.state.game_server_host,
                game_server_port=request.app.state.game_server_port,
            )
            return {"ok": True, "message": "Регистрация успешна!", "request_id": req.Request_Id}
        except ValueError as e:
            if str(e) == "limit_exceeded":
                raise HTTPException(status_code=403, detail="limit_exceeded")
            if str(e) == "login_taken":
                raise HTTPException(status_code=409, detail="login_taken")
            if str(e) == "not_in_group":
                raise HTTPException(status_code=403, detail="not_in_telegram_group")
            raise HTTPException(status_code=400, detail="bad_request")
        except RuntimeError as e:
            error_msg = str(e)
            logger.error(f"RuntimeError during registration: {error_msg}")
            if "game_server" in error_msg:
                raise HTTPException(status_code=502, detail=error_msg)
            raise HTTPException(status_code=500, detail="internal_error")
        except Exception as e:
            logger.exception(f"Unexpected error during registration: {e}")
            raise HTTPException(status_code=502, detail=f"unexpected_error: {type(e).__name__}")

    return router


