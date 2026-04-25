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

def obtener_compras(mercado):
    compras = []
    page = 1

    while True:
        nonce = str(int(time.time() * 1000))
        path = f"/markets/{mercado}/trades?page={page}"
        method = "GET"

        firma = firma_buda(BUDA_API_SECRET, method, path, nonce)

        headers = {
            "X-SBTC-APIKEY": BUDA_API_KEY,
            "X-SBTC-NONCE": nonce,
            "X-SBTC-SIGNATURE": firma,
        }

        url = BASE_URL + path
        r = requests.get(url, headers=headers, timeout=10)

        if r.status_code != 200:
            print(f"Error trades {mercado}: {r.text}")
            break

        data = r.json()
        trades = data.get("trades", [])

        if not trades:
            break

        for t in trades:
            # 🔑 esto detecta tus compras reales
            if t.get("maker_side", "").lower() == "sell":
                compras.append(t)

        if len(trades) < 20:
            break

        page += 1

    return compras

if __name__ == "__main__":
    main()
