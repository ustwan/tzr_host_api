from fastapi import FastAPI, HTTPException
import os
import httpx

app = FastAPI(title="API_1 server_status")

API_FATHER_URL = os.getenv("API_FATHER_URL", "http://api_father:9000")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/server/status")
async def server_status():
    url = f"{API_FATHER_URL}/internal/constants"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            consts = r.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"api_father error: {e}")

    # Сжимаем в удобный JSON (ключевые поля + meta)
    response = {
        "server_status": consts.get("ServerStatus", {}).get("value"),
        "rates": {
            "exp": consts.get("RateExp", {}).get("value"),
            "pvp": consts.get("RatePvp", {}).get("value"),
            "pve": consts.get("RatePve", {}).get("value"),
            "color_mob": consts.get("RateColorMob", {}).get("value"),
            "skill": consts.get("RateSkill", {}).get("value"),
        },
        "client_status": consts.get("CLIENT_STATUS", {}).get("value"),
        "_meta": {k: v.get("description") for k, v in consts.items()},
    }
    return response
