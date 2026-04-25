import requests
import os
import hmac
import hashlib
import time
import pytz
from datetime import datetime
from urllib.parse import quote

# ─── CONFIGURACIÓN ───────────────────────────────────────
TELEFONO       = os.environ["TELEFONO"]
APIKEY_BOT     = os.environ["APIKEY_BOT"]
BUDA_API_KEY   = os.environ["BUDA_API_KEY"]
BUDA_API_SECRET = os.environ["BUDA_API_SECRET"]
MERCADOS       = ["BTC-CLP", "ETH-CLP", "LTC-CLP", "USDC-CLP"]
BASE_URL       = "https://www.buda.com/api/v2"
# ─────────────────────────────────────────────────────────

def firma_buda(secret, method, path, nonce, body=""):
    mensaje = " ".join([method, path, body, str(nonce)])
    return hmac.new(
        secret.encode(),
        mensaje.encode(),
        hashlib.sha384
    ).hexdigest()

def headers_privados(method, path):
    nonce = str(int(time.time() * 1000))
    return {
        "X-SBTC-APIKEY":    BUDA_API_KEY,
        "X-SBTC-NONCE":     nonce,
        "X-SBTC-SIGNATURE": firma_buda(BUDA_API_SECRET, method, path, nonce),
        "Content-Type":     "application/json"
    }

def obtener_ticker(mercado):
    url = f"{BASE_URL}/markets/{mercado}/ticker"
    r   = requests.get(url, timeout=10)
    t   = r.json()["ticker"]
    return {
        "precio":       float(t["last_price"][0]),
        "bid":          float(t["max_bid"][0]),
        "ask":          float(t["min_ask"][0]),
        "variacion_24h": float(t["price_variation_24h"]) * 100,
    }

def obtener_ultima_compra(mercado):
    """Obtiene el precio promedio de las últimas órdenes de compra ejecutadas"""
    path = f"/api/v2/markets/{mercado}/orders"
    url  = f"{BASE_URL}/markets/{mercado}/orders"
    h    = headers_privados("GET", path)
    params = {"state": "traded", "order_type": "bid", "per": 5}

    try:
        r    = requests.get(url, headers=h, params=params, timeout=10)
        data = r.json()
        ordenes = data.get("orders", [])

        if not ordenes:
            return None, None

        # Calcular precio promedio ponderado de las últimas compras
        total_monto  = 0
        total_valor  = 0
        for orden in ordenes:
            precio = float(orden["price"][0]) if orden["price"][0] else 0
            monto  = float(orden["traded_amount"][0]) if orden["traded_amount"][0] else 0
            if precio > 0 and monto > 0:
                total_monto += monto
                total_valor += precio * monto

        if total_monto == 0:
            return None, None

        precio_promedio = total_valor / total_monto
        return precio_promedio, len(ordenes)

    except Exception as e:
        return None, None

def construir_mensaje():
    chile = pytz.timezone("America/Santiago")
    ahora = datetime.now(chile).strftime("%d/%m/%Y %H:%M")
    lineas = [
        f"🪙 *Reporte Cripto Buda.com*",
        f"📅 {ahora}",
        "─────────────────────",
    ]

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

            # Comparar con precio de compra propio
            precio_compra, n_ordenes = obtener_ultima_compra(mercado)
            if precio_compra and precio_compra > 0:
                diff_pct = ((t["precio"] - precio_compra) / precio_compra) * 100
                diff_clp = t["precio"] - precio_compra
                emoji_diff = "🟢" if diff_pct >= 0 else "🔴"
                lineas += [
                    f"  ────────────────────",
                    f"  📊 Vs tus compras ({n_ordenes} órdenes):",
                    f"  Precio compra prom: ${precio_compra:>12,.0f}",
                    f"  Diferencia : {emoji_diff} {diff_pct:+.2f}% (${diff_clp:>+12,.0f})",
                    f"  {'💡 Considera VENDER' if diff_pct >= 5 else '⏳ Mantener posición' if diff_pct >= 0 else '📉 En pérdida'}",
                ]
            else:
                lineas.append(f"  📊 Sin órdenes de compra registradas")

        except Exception as e:
            lineas.append(f"\n❌ {mercado}: error")

    lineas += [
        "\n─────────────────────",
        "_Reporte automático Buda.com_"
    ]
    return "\n".join(lineas)

def enviar_whatsapp(mensaje):
    url = (
        f"https://api.callmebot.com/whatsapp.php"
        f"?phone={TELEFONO}"
        f"&text={quote(mensaje)}"
        f"&apikey={APIKEY_BOT}"
    )
    r = requests.get(url, timeout=15)
    print("✅ WhatsApp enviado" if r.status_code == 200 else f"❌ Error: {r.status_code}")

def main():
    mensaje = construir_mensaje()
    print(mensaje)
    enviar_whatsapp(mensaje)

if __name__ == "__main__":
    main()
