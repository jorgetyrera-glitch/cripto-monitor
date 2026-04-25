import requests
import os
import hmac
import hashlib
import time
import pytz
from datetime import datetime
from urllib.parse import quote

TELEFONO        = os.environ["TELEFONO"]
APIKEY_BOT      = os.environ["APIKEY_BOT"]
BUDA_API_KEY    = os.environ["BUDA_API_KEY"]
BUDA_API_SECRET = os.environ["BUDA_API_SECRET"]
MERCADOS        = ["BTC-CLP", "ETH-CLP", "LTC-CLP", "USDC-CLP"]
BASE_URL        = "https://www.buda.com/api/v2"

def firma_buda(secret, method, path, nonce, body=""):
    mensaje = nonce + method + path + body
    return hmac.new(
        secret.encode(),
        mensaje.encode(),
        hashlib.sha384
    ).hexdigest()

def obtener_ultima_compra(mercado):
    nonce  = str(int(time.time() * 1000))
path   = f"/markets/{mercado}/orders"
method = "GET"

firma  = firma_buda(BUDA_API_SECRET, method, path, nonce)

    headers = {
    "X-SBTC-APIKEY": BUDA_API_KEY,
    "X-SBTC-NONCE": nonce,
    "X-SBTC-SIGNATURE": firma,
}

    url    = f"{BASE_URL}/markets/{mercado}/orders"
    params = {"state": "traded", "order_type": "bid", "per": 5}
    r      = requests.get(url, headers=headers, params=params, timeout=10)

    print(f"\n--- {mercado} ---")
    print(f"Status: {r.status_code}")
    print(f"Respuesta: {r.text[:500]}")
    return r.json()

def main():
    for mercado in MERCADOS:
        try:
            obtener_ultima_compra(mercado)
        except Exception as e:
            print(f"Error {mercado}: {e}")

if __name__ == "__main__":
    main()
