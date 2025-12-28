import os
import requests

BASE_URL = "https://api.elsevier.com"

class ElsevierClient:
    def __init__(self, api_key: str | None = None, timeout: int = 15):
        self.api_key = api_key or os.getenv("ELSEVIER_API_KEY")
        self.timeout = timeout
        if not self.api_key:
            raise RuntimeError("ELSEVIER_API_KEY is not set. Please export ELSEVIER_API_KEY.")

    @property
    def headers(self) -> dict:
        return {"X-ELS-APIKey": self.api_key, "Accept": "application/json"}

    def get(self, path: str, params: dict | None = None) -> dict:
        url = f"{BASE_URL}{path}"
        r = requests.get(url, headers=self.headers, params=params, timeout=self.timeout)
        if not r.ok:
            return {"success": False, "error": f"API Error: {r.status_code}", "details": r.text[:500]}
        return {"success": True, "data": r.json()}
