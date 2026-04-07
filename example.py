"""
example.py — fetch your Netspend transactions and print them.

Before running:
  1. Capture your token (see README).
  2. Set TOKEN below, or set the NS_TOKEN environment variable.
"""

import os
from netspend import NetspendClient

TOKEN = os.environ.get("NS_TOKEN", "paste-your-token-here")

client = NetspendClient(TOKEN)

print("Fetching last 2 months + pending...\n")
txns = client.get_transactions(months_back=2)

for t in txns:
    sign   = "+" if t["credit"] else "-"
    flag   = " [pending]" if t["pending"] else ""
    print(f"{t['ts'][:10]}  {sign}${abs(t['amount']):.2f}  "
          f"bal=${t['balance']:.2f}  {t['memo']}{flag}")

print(f"\n{len(txns)} transactions total.")