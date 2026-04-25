import os
import pytz
import requests
import hmac
import hashlib
import time
from datetime import datetime
from urllib.parse import quote

# ─── CONFIGURACIÓN ───────────────────────────────────────
TELEFONO        = os.environ["TELEFONO"]
APIKEY_BOT      = os.environ["APIKEY_BOT"]
BUDA_API_KEY    = os.environ["BUDA_API_KEY"]
BUDA_API_SECRET = os.environ["BUDA_API_SECRET"]

MERCADOS = ["btc-clp", "eth-clp", "ltc-clp", "usdc-clp"]
BASE_URL = "https://www.buda.com/api/v2"
# ─────────────────────────────────────────────────────────


# ─── HEADERS AUTENTICADOS ─────────────────────────────────
def buda_headers(method, path):
    nonce = str(int(time.time() * 1000))
    message = nonce + method + path
    signature = hmac.new(
        BUDA_API_SECRET.encode(),
        message.encode(),
        hashlib.sha384
    ).hexdigest()

    return {
        "X-SBTC-APIKEY": BUDA_API_KEY,
        "X-SBTC-NONCE": nonce,
        "X-SBTC-SIGNATURE": signature,
        "Content-Type": "application/json"
    }


# ─── TICKER (PRECIO ACTUAL) ───────────────────────────────
def obtener_ticker(mercado):
    url = f"{BASE_URL}/markets/{mercado}/ticker"
    r = requests.get(url)
    data = r.json()["ticker"]

    return {
        "last": float(data["last_price"][0]),
        "bid": float(data["max_bid"][0]),
        "ask": float(data["min_ask"][0]),
        "variation": float(data["price_variation_24h"]),
    }


# ─── ÓRDENES (TUS COMPRAS) ────────────────────────────────
def obtener_compras(mercado):
    path = f"/markets/{mercado}/orders"
    url = BASE_URL + path

    headers = buda_headers("GET", path)
    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        print(f"Error órdenes {mercado}: {r.text}")
        return []

    orders = r.json().get("orders", [])

    compras = [
        o for o in orders
        if o["type"] == "Bid" and o["state"] == "traded"
    ]

    return compras


def precio_promedio_compras(compras):
    if not compras:
        return None, 0

    total = 0
    cantidad = 0

    for o in compras:
        price = float(o["price"][0])
        amount = float(o["amount"][0])
        total += price * amount
        cantidad += amount

    if cantidad == 0:
        return None, 0

    return total / cantidad, len(compras)


# ─── MENSAJE ─────────────────────────────────────────────
def construir_mensaje():
    chile = pytz.timezone("America/Santiago")
    ahora = datetime.now(chile).strftime("%d/%m/%Y %H:%M")

    lineas = [
        "🪙 *Reporte Cripto Buda*",
        f"📅 {ahora}",
        "─────────────────────",
    ]

    for mercado in MERCADOS:
        try:
            ticker = obtener_ticker(mercado)

            base = mercado.split("-")[0].upper()
            precio_actual = ticker["last"]
            variacion = ticker["variation"]
            bid = ticker["bid"]
            ask = ticker["ask"]

            emoji = "📈" if variacion >= 0 else "📉"

            lineas += [
                f"\n*{base}*",
                f"  Precio : ${precio_actual:,.0f} CLP",
                f"  Compra : ${bid:,.0f}",
                f"  Venta  : ${ask:,.0f}",
                f"  24h    : {emoji} {variacion:.2f}%",
            ]

            compras = obtener_compras(mercado)
            promedio, n = precio_promedio_compras(compras)

            if promedio:
                diff_pct = ((precio_actual - promedio) / promedio) * 100
                diff_clp = precio_actual - promedio

                emoji_diff = "🟢" if diff_pct >= 0 else "🔴"

                decision = (
                    "💡 VENDER" if diff_pct >= 5 else
                    "⏳ MANTENER" if diff_pct >= 0 else
                    "📉 EN PÉRDIDA"
                )

                lineas += [
                    "  ─────────────────",
                    f"  📊 Vs {n} compras:",
                    f"  Promedio : ${promedio:,.0f}",
                    f"  Resultado: {emoji_diff} {diff_pct:.2f}% (${diff_clp:,.0f})",
                    f"  {decision}",
                ]
            else:
                lineas.append("  📊 Sin compras")

        except Exception as e:
            lineas.append(f"\n❌ {mercado}: {e}")

    lineas.append("\n─────────────────────")
    return "\n".join(lineas)


# ─── WHATSAPP ────────────────────────────────────────────
def enviar_whatsapp(mensaje):
    url = (
        f"https://api.callmebot.com/whatsapp.php"
        f"?phone={TELEFONO}"
        f"&text={quote(mensaje)}"
        f"&apikey={APIKEY_BOT}"
    )

    r = requests.get(url)
    print("✅ Enviado" if r.status_code == 200 else r.text)


# ─── MAIN ────────────────────────────────────────────────
def main():
    mensaje = construir_mensaje()
    print(mensaje)
    enviar_whatsapp(mensaje)


if __name__ == "__main__":
    main()
