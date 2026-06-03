"""
get_token.py — Log in to Netspend and print your API token.

Run this when your token has expired.
"""

import getpass
import requests

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

_DEVICE_FP = (
    "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;0400cPQTmysTpIrjK9GFecOQizm"
    "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"
)

username = input("Netspend username (email): ").strip()
password = getpass.getpass("Password: ")

print("Logging in...")
s = requests.Session()
s.headers.update(_LOGIN_HEADERS)
s.get("https://www.netspend.com/account/login", timeout=15)
resp = s.post(
    "https://www.netspend.com/profile-api/login",
    json={
        "username": username,
        "password": password,
        "auth_type": "password",
        "device_fingerprint": _DEVICE_FP,
    },
    timeout=30,
)
resp.raise_for_status()
data = resp.json()

if data.get("ooba_required"):
    partial = data.get("token", "")
    code = input("Enter the one-time code sent to your phone/email: ").strip()
    resp2 = requests.post(
        "https://www.netspend.com/profile-api/ooba/verify",
        headers={**_LOGIN_HEADERS, "X-Ns-Access_token": partial},
        json={"ooba_passcode": code},
        timeout=30,
    )
    resp2.raise_for_status()
    token = resp2.json().get("token") or partial
else:
    token = data.get("token", "")

if not token:
    print(f"ERROR: No token in response. Keys: {list(data.keys())}")
else:
    print(f"Token: {token}")
