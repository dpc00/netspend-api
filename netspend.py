"""
netspend.py — Unofficial Python client for the Netspend internal API.

Fetches your own transaction data: monthly statements and pending transactions.
Discovered via mitmproxy traffic capture against the Netspend web app.

Usage:
    from netspend import NetspendClient, login

    # One-time: get a token (device fingerprint is bundled)
    token = login("your_username", "your_password")

    client = NetspendClient(token)
    statement = client.get_statement(2026, 4)   # April 2026
    pending   = client.get_pending()

    for txn in statement["transactions"]:
        date   = txn["date"]
        amount = txn["amount"] / 100          # cents → dollars
        credit = txn["credit"]                # True = money in
        memo   = txn["memo"]
        bal    = txn["running_balance"] / 100
        print(f"{date}  {'+'if credit else '-'}${amount:.2f}  {memo}  bal=${bal:.2f}")
"""

import requests

# ── API base and required headers ─────────────────────────────────────────────

_BASE = "https://app.netspend.com"

_SYNC_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.0.0 Safari/537.36"
    ),
    "x-ns-client": (
        "app=spectrum; platform=web; brand=netspend; "
        "platformType=web; version=oac-v2.2.3; distributor=walgreens"
    ),
    "x-ns-variant": "variant://app.netspend.com",
    "Accept": "*/*",
    "Referer": (
        "https://app.netspend.com/app/dashboard"
        "?drawer=transactions&isWW=true"
    ),
}

_LOGIN_URL = "https://www.netspend.com/profile-api/login"

_LOGIN_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.0.0 Safari/537.36"
    ),
    "X-NS-Client": (
        "app=Account Center; platform=web; platformType=web; "
        "brand=netspend; version=2026.14.0.1050"
    ),
    "X-NS-Variant": "variant://app.netspend.com",
    "Content-Type": "application/json",
    "Accept": "*/*",
    "Origin": "https://www.netspend.com",
    "Referer": "https://www.netspend.com/account/login",
}

# Device fingerprint captured from a real browser session via mitmproxy.
# Netspend uses this for bot detection; without it login may be rejected.
_DEVICE_FP = (
    "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;0400cPQTmysTpIrjK9GFecOQizm"
    "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"
)


# ── Login ─────────────────────────────────────────────────────────────────────

def login(username: str, password: str, device_fingerprint: str = _DEVICE_FP) -> str:
    """
    Authenticate with Netspend and return an access token.

    device_fingerprint defaults to a captured browser fingerprint (_DEVICE_FP).
    The token typically expires after a few days.

    Returns the token string.
    Raises requests.HTTPError on failure.
    If ooba_required is True in the response, a one-time code was sent to
    your phone/email — call verify_ooba() with the partial token and code.
    """
    s = requests.Session()
    s.headers.update(_LOGIN_HEADERS)
    # Visit login page to establish session cookies
    s.get("https://www.netspend.com/account/login", timeout=15)
    resp = s.post(
        _LOGIN_URL,
        json={
            "username": username,
            "password": password,
            "auth_type": "password",
            "device_fingerprint": device_fingerprint,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("ooba_required"):
        raise OOBARequired(data.get("token", ""), "One-time code required")
    return data["token"]


def verify_ooba(partial_token: str, code: str) -> str:
    """
    Complete login when a one-time code (OOBA) was required.
    Pass the partial token from OOBARequired and the code from your phone/email.
    Returns the final access token.
    """
    resp = requests.post(
        "https://www.netspend.com/profile-api/ooba/verify",
        headers={**_LOGIN_HEADERS, "X-Ns-Access_token": partial_token},
        json={"ooba_passcode": code},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("token") or partial_token


class OOBARequired(Exception):
    """Raised by login() when Netspend requires a one-time code."""
    def __init__(self, partial_token: str, message: str):
        super().__init__(message)
        self.partial_token = partial_token


# ── Client ────────────────────────────────────────────────────────────────────

class NetspendClient:
    """
    Fetch transaction data from the Netspend internal API.

    token: obtained from login() or captured via mitmproxy (see README).
    """

    def __init__(self, token: str):
        self.token = token
        self._headers = {**_SYNC_HEADERS, "X-Ns-Access_token": token}

    def _get(self, path: str) -> dict:
        url = f"{_BASE}{path}"
        resp = requests.get(url, headers=self._headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_statement(self, year: int, month: int) -> dict:
        """
        Fetch a monthly statement.

        Returns a dict with keys:
          transactions  — list of transaction dicts
          balance       — dict with 'ending' balance (in cents)

        Each transaction has:
          date            — "MM-DD-YYYY HH:MM:SS +0000"
          amount          — integer cents (always positive)
          credit          — True if money came in, False if money went out
          running_balance — integer cents
          memo            — description string
        """
        return self._get(f"/webapi/v1/statement/debit/{year}/{month}")

    def get_pending(self) -> dict:
        """
        Fetch pending (not yet posted) transactions.
        Same structure as get_statement().
        """
        return self._get("/webapi/v1/transactions/debit/pending")

    def get_transactions(self, months_back: int = 2) -> list:
        """
        Convenience method: fetch transactions for the last N months plus pending.
        Returns a flat sorted list of dicts:
          ts      — ISO timestamp string (UTC)
          amount  — dollars (positive = credit, negative = debit)
          balance — running balance in dollars
          memo    — description
          credit  — bool
          pending — bool
        """
        import datetime

        today = datetime.date.today()
        results = []

        for delta in range(months_back - 1, -1, -1):
            d = today.replace(day=1)
            for _ in range(delta):
                d = (d.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
            try:
                stmt = self.get_statement(d.year, d.month)
            except requests.HTTPError:
                continue
            for t in stmt.get("transactions", []):
                results.append(_normalize(t, pending=False))

        try:
            pend = self.get_pending()
            for t in pend.get("transactions", []):
                results.append(_normalize(t, pending=True))
        except requests.HTTPError:
            pass

        results.sort(key=lambda x: x["ts"])
        return results


def _normalize(t: dict, pending: bool) -> dict:
    import datetime
    raw = t["date"]
    try:
        dt = datetime.datetime.strptime(raw[:25], "%m-%d-%Y %H:%M:%S %z")
        ts = dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        ts = datetime.datetime.strptime(raw[:10], "%m-%d-%Y").strftime(
            "%Y-%m-%dT00:00:00Z"
        )
    credit = t["credit"]
    amt = t["amount"] / 100
    return {
        "ts":      ts,
        "amount":  amt if credit else -amt,
        "balance": t["running_balance"] / 100,
        "memo":    t.get("memo", ""),
        "credit":  credit,
        "pending": pending,
    }