"""
example.py — Log in to Netspend and print recent transactions.
"""

import getpass
from netspend import NetspendClient, login, OOBARequired, verify_ooba

username = input("Netspend username (email): ").strip()
password = getpass.getpass("Password: ")

print("Logging in...")
try:
    token = login(username, password)
except OOBARequired as e:
    code = input("Enter the one-time code from your phone/email: ").strip()
    token = verify_ooba(e.partial_token, code)

client = NetspendClient(token)
txns = client.get_transactions(months_back=2)

for t in txns:
    sign = "+" if t["credit"] else "-"
    flag = " [pending]" if t["pending"] else ""
    print(
        f"{t['ts'][:10]}  {sign}${abs(t['amount']):.2f}  bal=${t['balance']:.2f}  {t['memo']}{flag}"
    )

print(f"\n{len(txns)} transactions total.")
