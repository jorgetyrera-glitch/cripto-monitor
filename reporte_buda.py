import os
import hmac
import hashlib
import time
import pytz
import requests
from datetime import datetime
from urllib.parse import quote

TELEFONO        = os.environ["TELEFONO"]
APIKEY_BOT      = os.environ["APIKEY_BOT"]
BUDA_API_KEY    = os.environ["BUDA_API_KEY"]
BUDA_API_SECRET = os.environ["BUDA_API_SECRET"]
MERCADOS        = ["BTC-CLP", "ETH-CLP", "LTC-CLP", "USDC-CLP"]

def probar_firma(label, msg):
    """Genera firma y prueba el endpoint de balances"""
    nonce = str(int(time.time() * 1000))
    firma = hmac.new(
        BUDA_API_SECRET.encode("utf-8"),
        msg.replace("{NONCE}", nonce).encode("utf-8"),
        hashlib.sha384
    ).hexdigest()
    headers = {
        "X-SBTC-APIKEY":    BUDA_API_KEY,
        "X-SBTC-NONCE":     nonce,
        "X-SBTC-SIGNATURE": firma,
    }
    r = requests.get("https://www.buda.com/api/v2/balances", headers=headers, timeout=10)
    print(f"[{label}] status={r.status_code} | resp={r.text[:100]}")
    return r.status_code == 200

def main():
    path  = "/api/v2/balances"
    nonce = str(int(time.time() * 1000))

    formatos = [
        ("GET path body nonce",   f"GET {path}  {nonce}"),
        ("GET path nonce",        f"GET {path} {nonce}"),
        ("path nonce",            f"{path} {nonce}"),
        ("GET path _ nonce",      f"GET {path} _ {nonce}"),
    ]

    for label, msg in formatos:
        firma = hmac.new(
            BUDA_API_SECRET.encode("utf-8"),
            msg.encode("utf-8"),
            hashlib.sha384
        ).hexdigest()
        headers = {
            "X-SBTC-APIKEY":    BUDA_API_KEY,
            "X-SBTC-NONCE":     nonce,
            "X-SBTC-SIGNATURE": firma,
        }
        r = requests.get("https://www.buda.com/api/v2/balances", headers=headers, timeout=10)
        print(f"[{label}] → status={r.status_code} | {r.text[:120]}")
        time.sleep(1)  # evitar rate limit

    # Reporte público sin autenticación
    chile = pytz.timezone("America/Santiago")
    ahora = datetime.now(chile).strftime("%d/%m/%Y %H:%M")
    lineas = [f"🪙 *Reporte Cripto Buda.com*", f"📅 {ahora}", "─────────────────────"]

    for mercado in MERCADOS:
        try:
            r = requests.get(f"https://www.buda.com/api/v2/markets/{mercado}/ticker", timeout=10)
            t = r.json()["ticker"]
            base   = mercado.split("-")[0]
            precio = float(t["last_price"][0])
            bid    = float(t["max_bid"][0])
            ask    = float(t["min_ask"][0])
            var    = float(t["price_variation_24h"]) * 100
            signo  = "+" if var >= 0 else ""
            lineas += [
                f"\n*{base}*",
                f"  Precio : ${precio:>15,.0f} CLP",
                f"  Compra : ${bid:>15,.0f}",
                f"  Venta  : ${ask:>15,.0f}",
                f"  24h    : {signo}{var:.2f}%",
                f"  Comparacion pendiente (ajustando autenticacion)",
            ]
        except Exception as e:
            lineas.append(f"\nError {mercado}: {e}")
