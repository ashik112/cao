from fastapi import APIRouter
import requests
from app.config import SERVICES

router = APIRouter()

@router.get("/health")
def health():
    return {"ok": True}

@router.get("/health/services")
def health_services():
    out = {}
    for name, conf in SERVICES.items():
        url = conf["base_url"].rstrip("/") + conf.get("health_path", "/health")
        try:
            r = requests.get(url, timeout=(2, 2))
            out[name] = {"ok": r.status_code == 200, "status_code": r.status_code}
        except Exception as e:
            out[name] = {"ok": False, "error": str(e)}
    return out
