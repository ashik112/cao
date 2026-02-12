import requests
from typing import Dict, Any, Optional
from app.config import SERVICES, INTERNAL_API_KEY, HTTP_CONNECT_TIMEOUT_S, HTTP_READ_TIMEOUT_S

class ServiceCallError(RuntimeError):
    def __init__(self, code: str, message: str, retryable: bool, details: Optional[dict] = None):
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.details = details

class HTTPServiceClient:
    def _headers(self, service_conf: dict, idempotency_key: str) -> Dict[str, str]:
        h = {"Content-Type": "application/json", "Idempotency-Key": idempotency_key}
        auth = service_conf.get("auth", {"type": "none"})
        if auth.get("type") == "api_key_header":
            header_name = auth.get("header", "X-Internal-Key")
            if INTERNAL_API_KEY:
                h[header_name] = INTERNAL_API_KEY
        elif auth.get("type") == "bearer":
            if INTERNAL_API_KEY:
                h["Authorization"] = f"Bearer {INTERNAL_API_KEY}"
        return h

    def _parse_error(self, resp: requests.Response) -> dict:
        try:
            body = resp.json()
        except Exception:
            body = None

        if isinstance(body, dict) and body.get("status") == "FAILED" and isinstance(body.get("error"), dict):
            err = body["error"]
            return {
                "code": err.get("code", "SERVICE_ERROR"),
                "message": err.get("message", f"HTTP {resp.status_code}"),
                "retryable": bool(err.get("retryable", resp.status_code >= 500)),
                "details": err,
            }

        return {
            "code": "SERVICE_HTTP_ERROR",
            "message": f"Service returned HTTP {resp.status_code}",
            "retryable": resp.status_code >= 500,
            "details": body if isinstance(body, dict) else None,
        }

    def call(self, service_name: str, envelope: Dict[str, Any], timeout_s: int) -> Dict[str, Any]:
        conf = SERVICES.get(service_name)
        if not conf:
            raise ServiceCallError("UNKNOWN_SERVICE", f"No config for {service_name}", False)

        url = conf["base_url"].rstrip("/") + conf["execute_path"]
        idem = f"{envelope['meta']['job_id']}:{envelope['meta']['step_index']}:{service_name}"

        connect_t = HTTP_CONNECT_TIMEOUT_S
        read_t = min(float(timeout_s), float(HTTP_READ_TIMEOUT_S))
        timeout = (connect_t, read_t)

        try:
            resp = requests.post(url, json=envelope, headers=self._headers(conf, idem), timeout=timeout)
        except requests.Timeout as e:
            raise ServiceCallError("SERVICE_TIMEOUT", str(e), True)
        except requests.RequestException as e:
            raise ServiceCallError("SERVICE_UNREACHABLE", str(e), True)

        if resp.status_code < 200 or resp.status_code >= 300:
            err = self._parse_error(resp)

            # map common "busy" scenarios
            if resp.status_code in (429, 503):
                err["code"] = "RESOURCE_EXHAUSTED"
                err["retryable"] = True

            raise ServiceCallError(err["code"], err["message"], err["retryable"], err.get("details"))

        try:
            out = resp.json()
        except Exception:
            raise ServiceCallError("BAD_RESPONSE", "Service returned non-JSON", True)

        if out.get("status") != "SUCCESS":
            err = out.get("error", {})
            raise ServiceCallError(
                err.get("code", "SERVICE_FAILED"),
                err.get("message", f"{service_name} failed"),
                bool(err.get("retryable", True)),
                err
            )

        if "data" not in out or not isinstance(out["data"], dict):
            raise ServiceCallError("BAD_RESPONSE", "Missing data object", True)

        if "metrics" in out and not isinstance(out["metrics"], dict):
            raise ServiceCallError("BAD_RESPONSE", "metrics must be an object", True)

        out.setdefault("metrics", {})
        return out
