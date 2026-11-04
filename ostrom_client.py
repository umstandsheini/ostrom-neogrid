"""Minimal client for the private Ostrom app API (reverse engineered from app 6.4.0, unverified)."""
import json
import urllib.error
import urllib.request
from http.cookiejar import CookieJar

API = "https://api.ostrom.de/v1"


class OstromError(Exception):
    def __init__(self, status, body):
        super().__init__(f"HTTP {status}: {body[:300]}")
        self.status = status


class OstromClient:
    def __init__(self, base=API):
        self.base = base
        self.jar = CookieJar()
        self.token = None
        self.cookie_flags = {}
        self.set_cookies = {}  # name -> value, parsed from Set-Cookie headers
        self.http = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def request(self, method, path, body=None, headers=None, auth="bearer", base=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request((base or self.base) + path, data=data, method=method)
        req.add_header("Accept", "application/json")
        req.add_header("X-APP-VERSION", "6.4.0")
        if self.token and auth == "session":
            req.add_header("X-SESSION-TOKEN", self.token)
        elif self.token and auth == "bearer":
            req.add_header("Authorization", "Bearer " + self.token)
        elif auth == "cookie":
            req.add_header("Cookie", "; ".join(f"{k}={v}" for k, v in self.set_cookies.items()))
        if data is not None:
            req.add_header("Content-Type", "application/json")
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            with self.http.open(req, timeout=20) as r:
                raw = r.read().decode()
                self._grab_cookies(r.headers.get_all("Set-Cookie") or [])
        except urllib.error.HTTPError as e:
            raise OstromError(e.code, e.read().decode(errors="replace")) from None
        return json.loads(raw) if raw else None

    def _grab_cookies(self, headers):
        for h in headers:
            name, _, rest = h.partition("=")
            self.set_cookies[name.strip()] = rest.split(";", 1)[0]
            self.cookie_flags[name.strip()] = [a.split("=")[0].strip() + ("=" + a.split("=")[1] if a.split("=")[0].strip().lower() in ("domain", "path", "samesite") else "") for a in rest.split(";")[1:]]

    def cookie_attrs(self):
        """Attribute names only (no values) of cookies seen, for debugging."""
        return sorted(self.set_cookies)

    def login(self, email, password):
        resp = self.request("POST", "/auth/login",
                            {"email": email, "password": password, "application": "MOBILE_APP"})
        # verified live: the API accepts "Authorization: Bearer <access_token cookie>"
        self.token = self.set_cookies.get("access_token") or resp.get("accessToken")
        return resp

    def get(self, path, auth="bearer", base=None):
        return self.request("GET", path, auth=auth, base=base)
