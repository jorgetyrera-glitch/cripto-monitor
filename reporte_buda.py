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
BASE_URL        = "https://www.buda.com/api/v2"

def generar_firma(secret, nonce, method, path, body=""):
    # Probamos los dos formatos posibles que usa Buda
    msg = " ".join([method.upper(), path, body, nonce])
    return hmac.new(
        secret.encode("utf-8"),
        msg.encode("utf-8"),
        hashlib.sha384
    ).hexdigest()

def request_privado(path, params=None):
    nonce = str(int(time.time() * 1000))
    firma = generar_firma(BUDA_API_SECRET, nonce, "GET", path)
    headers = {
        "X-SBTC-APIKEY":    BUDA_API_KEY,
        "X-SBTC-NONCE":     nonce,
        "X-SBTC-SIGNATURE": firma,
        "Content-Type":     "application/json",
    }
    r = requests.get(BASE_URL + path, headers=headers, params=params, timeout=10)
    print(f"[DEBUG] {path} → {r.status_code}")
    print(f"[DEBUG] respuesta completa: {r.text[:500]}")
    return r

def obtener_ticker(mercado):
    r = requests.get(f"{BASE_URL}/markets/{mercado}/ticker", timeout=10)
    t = r.json()["ticker"]
    return {
        "precio":        float(t["last_price"][0]),
        "bid":           float(t["max_bid"][0]),
        "ask":           float(t["min_ask"][0]),
        "variacion_24h": float(t["price_variation_24h"]) * 100,
    }

def main():
    # Test 1: balances (endpoint privado simple)
    print("\n=== TEST: /api/v2/balances ===")
    request_privado("/api/v2/balances")

    # Test 2: mis órdenes BTC-CLP en minúsculas
    print("\n=== TEST: /api/v2/markets/btc-clp/orders ===")
    request_privado("/api/v2/markets/btc-clp/orders", params={"per": 5})

    # Test 3: endpoint alternativo
    print("\n=== TEST: /api/v2/orders ===")
    request_privado("/api/v2/orders", params={"market_id": "BTC-CLP", "per": 5})

    # Igual enviamos el reporte de precios sin comparación
    chile = pytz.timezone("America/Santiago")
    ahora = datetime.now(chile).strftime("%d/%m/%Y %H:%M")
    lineas = [f"🪙 *Reporte Cripto Buda.com*", f"📅 {ahora}", "─────────────────────"]

    for mercado in MERCADOS:
        try:
            t    = obtener_ticker(mercado)
            base = mercado.split("-")[0]
            emoji_24h = "📈" if t["variacion_24h"] >= 0 else "📉"
            lineas += [
                f"\n*{base}*",
                f"  Precio : ${t['precio']:>15,.0f} CLP",
                f"  Compra : ${t['bid']:>15,.0f}",
                f"  Venta  : ${t['ask']:>15,.0f}",
                f"  24h    : {emoji_24h} {t['variacion_24h']:+.2f}%",
            ]
        except Exception as e:
            lineas.append(f"\n❌ {mercado}: {e}")

    lineas += ["\n─────────────────────", "_Reporte automático Buda.com_"]
    mensaje = "\n".join(lineas)
    print(mensaje)

    url = f"https://api.callmebot.com/whatsapp.php?phone={TELEFONO}&text={quote(mensaje)}&apikey={APIKEY_BOT}"
    r = requests.get(url, timeout=15)
    print("✅ WhatsApp enviado" if r.status_code == 200 else f"❌ Error: {r.status_code}")

if __name__ == "__main__":
    main()
