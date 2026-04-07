"""
netspend.py — Unofficial Python client for the Netspend internal API.

Fetches your own transaction data: monthly statements and pending transactions.
Discovered via mitmproxy traffic capture against the Netspend web app.

Usage:
    from netspend import NetspendClient, login

    # One-time: get a token (see README for how to capture it)
    token = login("your_username", "your_password", device_fingerprint)

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
        "Chrome/124.0.0.0 Safari/537.36"
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
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "X-NS-Client": (
        "app=Account Center; platform=web; platformType=web; "
        "brand=netspend; version=2026.14.0.1050"
    ),
    "X-NS-Variant": "variant://app.netspend.com",
    "Accept": "*/*",
    "Origin": "https://www.netspend.com",
    "Referer": "https://www.netspend.com/account/login",
}


# ── Login ─────────────────────────────────────────────────────────────────────

def login(username: str, password: str, device_fingerprint: str) -> str:
    """
    Authenticate with Netspend and return an access token.

    The device_fingerprint must be captured from a real browser session —
    see README for instructions.  The token typically expires after a few days.

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