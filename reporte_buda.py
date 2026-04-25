import os
import sys
import hmac
import hashlib
import time
import requests
from urllib.parse import quote

print("=== INICIANDO SCRIPT ===", flush=True)

TELEFONO        = os.environ.get("TELEFONO", "")
APIKEY_BOT      = os.environ.get("APIKEY_BOT", "")
BUDA_API_KEY    = os.environ.get("BUDA_API_KEY", "")
BUDA_API_SECRET = os.environ.get("BUDA_API_SECRET", "")

print(f"API KEY presente: {'SI' if BUDA_API_KEY else 'NO'}", flush=True)
print(f"API SECRET presente: {'SI' if BUDA_API_SECRET else 'NO'}", flush=True)

nonce = str(int(time.time() * 1000))
print(f"Nonce: {nonce}", flush=True)

# Formato 1
path = "/api/v2/balances"
msg1 = f"GET {path}  {nonce}"
firma1 = hmac.new(BUDA_API_SECRET.encode(), msg1.encode(), hashlib.sha384).hexdigest()
headers1 = {"X-SBTC-APIKEY": BUDA_API_KEY, "X-SBTC-NONCE": nonce, "X-SBTC-SIGNATURE": firma1}
r1 = requests.get("https://www.buda.com/api/v2/balances", headers=headers1, timeout=10)
print(f"Formato1 [GET path body nonce]: status={r1.status_code} resp={r1.text[:150]}", flush=True)

time.sleep(2)

# Formato 2
nonce = str(int(time.time() * 1000))
msg2 = f"GET {path} {nonce}"
firma2 = hmac.new(BUDA_API_SECRET.encode(), msg2.encode(), hashlib.sha384).hexdigest()
headers2 = {"X-SBTC-APIKEY": BUDA_API_KEY, "X-SBTC-NONCE": nonce, "X-SBTC-SIGNATURE": firma2}
r2 = requests.get("https://www.buda.com/api/v2/balances", headers=headers2, timeout=10)
print(f"Formato2 [GET path nonce]: status={r2.status_code} resp={r2.text[:150]}", flush=True)

time.sleep(2)

# Formato 3 — sin método
nonce = str(int(time.time() * 1000))
msg3 = f"{path}  {nonce}"
firma3 = hmac.new(BUDA_API_SECRET.encode(), msg3.encode(), hashlib.sha384).hexdigest()
headers3 = {"X-SBTC-APIKEY": BUDA_API_KEY, "X-SBTC-NONCE": nonce, "X-SBTC-SIGNATURE": firma3}
r3 = requests.get("https://www.buda.com/api/v2/balances", headers=headers3, timeout=10)
print(f"Formato3 [path body nonce]: status={r3.status_code} resp={r3.text[:150]}", flush=True)

time.sleep(2)

# Formato 4 — con body vacío explícito
nonce = str(int(time.time() * 1000))
msg4 = " ".join(["GET", path, "", nonce])
firma4 = hmac.new(BUDA_API_SECRET.encode(), msg4.encode(), hashlib.sha384).hexdigest()
headers4 = {"X-SBTC-APIKEY": BUDA_API_KEY, "X-SBTC-NONCE": nonce, "X-SBTC-SIGNATURE": firma4}
r4 = requests.get("https://www.buda.com/api/v2/balances", headers=headers4, timeout=10)
print(f"Formato4 [GET path '' nonce]: status={r4.status_code} resp={r4.text[:150]}", flush=True)

print("=== FIN SCRIPT ===", flush=True)
