# netspend-api

Unofficial Python client for the Netspend internal API.

Netspend has no public API and no support for Plaid, Mint, or any third-party aggregator. Millions of people use Netspend prepaid cards — mostly for direct deposit of government benefits — with no programmatic access to their own transaction data.

This library fills that gap. The API endpoints were discovered by capturing traffic from the Netspend web app using [mitmproxy](https://mitmproxy.org/).

> **Note:** This accesses your own account data. Use it responsibly and only for your own account.

---

## Files

| File | Purpose |
|------|---------|
| `netspend.py` | The library — login, token handling, API calls |
| `example.py` | Run this to log in and print your transactions |
| `get_token.py` | Run this just to get a token (prints it to the screen) |

---

## Quick start

Install the one dependency:

```
pip install requests
```

Then run:

```
python example.py
```

It will ask for your Netspend username (email) and password, log in, and print your transactions for the current month. If Netspend sends a one-time code to your phone or email, it will ask for that too.

---

## What is the device fingerprint?

When you log in to the Netspend website, your browser sends a long encoded string called a **device fingerprint** along with your username and password. Netspend uses it for fraud detection — it is a snapshot of your browser's characteristics (screen size, fonts, plugins, hardware, etc.) that helps them tell a real user from a bot.

Without a valid fingerprint, the login request is rejected.

The fingerprint in this code (`_DEVICE_FP` in `netspend.py` and `get_token.py`) was captured from a real browser session using mitmproxy. It is baked in so you do not need to capture one yourself — just run the scripts and they work.

### Why does one fingerprint work for everyone?

Netspend uses the fingerprint for **scoring**, not hard validation. It checks whether the fingerprint looks plausible, not whether it matches the exact device that enrolled. A captured fingerprint from any real browser session passes that check. The same fingerprint has been used successfully across many logins over a long period.

### What if it stops working?

If Netspend tightens their checks and the bundled fingerprint starts getting rejected, you can capture a fresh one:

1. Install mitmproxy: `pip install mitmproxy`
2. Start it: `mitmproxy --listen-port 8080`
3. Set your browser to use `localhost:8080` as an HTTP/S proxy and install the mitmproxy CA certificate
4. Log in to [app.netspend.com](https://app.netspend.com) in that browser
5. In mitmproxy, find the POST request to `profile-api/login`
6. The request body contains `"device_fingerprint": "0400..."` — copy that value
7. Replace `_DEVICE_FP` in `netspend.py` and `get_token.py` with the new value

---

## What is the token?

After a successful login, Netspend returns a **token** — a long string that acts like a temporary password for the API. You include it in every API request as the `X-Ns-Access_token` header.

Tokens expire after a few days. When yours expires, the API starts returning 401 or 403 errors. Run `get_token.py` (or `example.py`) to log in again and get a fresh one.

---

## Understanding netspend.py

The file has three sections:

### 1. Constants and headers

Netspend's API requires specific HTTP headers on every request or it rejects the call. These are captured from real browser traffic:

- `_SYNC_HEADERS` — sent with every data-fetch request (statements, pending)
- `_LOGIN_HEADERS` — sent with the login request
- `_DEVICE_FP` — the browser fingerprint sent during login (see above)

### 2. Login functions

**`login(username, password)`**
Logs in and returns a token string. If Netspend requires a one-time code (two-factor auth), it raises `OOBARequired` instead — catch it, ask the user for their code, then call `verify_ooba()`.

**`verify_ooba(partial_token, code)`**
Completes the login when a one-time code was required. Returns the final token.

**`OOBARequired`**
An exception class. When raised, its `.partial_token` attribute holds the incomplete token you need to pass to `verify_ooba()`.

### 3. NetspendClient

Pass your token to create a client:

```python
client = NetspendClient(token)
```

**`client.get_statement(year, month)`**
Fetches one month of posted transactions. Returns a dict with a `transactions` list and a `balance` dict. Amounts are in **cents** (integer).

**`client.get_pending()`**
Fetches transactions that have been authorized but not yet posted. Same structure as `get_statement()`.

**`client.get_transactions(months_back=2)`**
The easiest method to use. Fetches the last N months of posted transactions plus any pending ones, converts amounts to **dollars** (float), and returns a flat sorted list. Each item looks like:

```python
{
  "ts":      "2026-06-03T12:34:56Z",   # date and time (UTC)
  "amount":  -23.90,                   # dollars; negative = you paid, positive = money in
  "balance": 421.06,                   # your running balance after this transaction
  "memo":    "DD *DOORDASH TACOBELL",  # description from Netspend
  "credit":  False,                    # True = money in, False = money out
  "pending": False                     # True if not yet posted
}
```

---

## API endpoints discovered

| Method | URL | Description |
|--------|-----|-------------|
| POST | `https://www.netspend.com/profile-api/login` | Authenticate |
| POST | `https://www.netspend.com/profile-api/ooba/verify` | Complete two-factor login |
| GET  | `https://app.netspend.com/webapi/v1/statement/debit/{year}/{month}` | Monthly statement |
| GET  | `https://app.netspend.com/webapi/v1/transactions/debit/pending` | Pending transactions |

---

## Disclaimer

This is an unofficial, community-developed tool. It is not affiliated with or endorsed by Netspend or its parent company. The API endpoints are internal and may change without notice. Use it to access your own account data only.
