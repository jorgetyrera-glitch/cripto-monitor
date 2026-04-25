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
    msg = " ".join([method.upper(), path, body, nonce])
    return hmac.new(
        secret.encode("utf-8"),
        msg.encode("utf-8"),
        hashlib.sha384
    ).hexdigest()

def request_privado(path, params=None):
    nonce  = str(int(time.time() * 1000))
    firma  = generar_firma(BUDA_API_SECRET, nonce, "GET", path)
    headers = {
        "X-SBTC-APIKEY":    BUDA_API_KEY,
        "X-SBTC-NONCE":     nonce,
        "X-SBTC-SIGNATURE": firma,
        "Content-Type":     "application/json",
    }
    url = BASE_URL + path
    r   = requests.get(url, headers=headers, params=params, timeout=10)
    print(f"[DEBUG] {path} → status {r.status_code}")
    print(f"[DEBUG] respuesta: {r.text[:300]}")
    return r.json()

def obtener_ticker(mercado):
    url = f"{BASE_URL}/markets/{mercado}/ticker"
    r   = requests.get(url, timeout=10)
    t   = r.json()["ticker"]
    return {
        "precio":        float(t["last_price"][0]),
        "bid":           float(t["max_bid"][0]),
        "ask":           float(t["min_ask"][0]),
        "variacion_24h": float(t["price_variation_24h"]) * 100,
    }

def obtener_compras(mercado):
    # Probamos el endpoint sin filtro de tipo para ver qué devuelve
    path = f"/api/v2/markets/{mercado}/orders"
    data = request_privado(path, params={"per": 50})
    ordenes = data.get("orders", [])
    print(f"[DEBUG] Total órdenes recibidas {mercado}: {len(ordenes)}")

    compras = []
    for o in ordenes:
        print(f"[DEBUG] orden → tipo: {o.get('order_type')} | estado: {o.get('state')} | precio: {o.get('price')}")
        try:
            tipo   = o.get("order_type", "")
            estado = o.get("state", "")
            precio = float(o["price"][0]) if o.get("price") and o["price"][0] else None
            monto  = float(o["traded_amount"][0]) if o.get("traded_amount") and o["traded_amount"][0] else None
            if "bid" in tipo and "traded" in estado and precio and monto and precio > 0:
                compras.append({"precio": precio, "monto": monto})
        except:
            continue
    return compras

def precio_promedio_ponderado(compras):
    if not compras:
        return None
    total_valor = sum(c["precio"] * c["monto"] for c in compras)
    total_monto = sum(c["monto"] for c in compras)
    return total_valor / total_monto if total_monto > 0 else None

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

            compras       = obtener_compras(mercado)
            precio_compra = precio_promedio_ponderado(compras)

            if precio_compra:
                diff_pct = ((t["precio"] - precio_compra) / precio_compra) * 100
                diff_clp = t["precio"] - precio_compra
                emoji    = "🟢" if diff_pct >= 0 else "🔴"
                decision = "💡 Considera VENDER" if diff_pct >= 5 else "⏳ Mantener" if diff_pct >= 0 else "📉 En pérdida"
                lineas += [
                    f"  ─────────────────",
                    f"  📊 Vs tus {len(compras)} compras:",
                    f"  Prom compra : ${precio_compra:>12,.0f}",
                    f"  Diferencia  : {emoji} {diff_pct:+.2f}% (${diff_clp:>+,.0f})",
                    f"  {decision}",
                ]
            else:
                lineas.append("  📊 Sin compras ejecutadas")

        except Exception as e:
            lineas.append(f"\n❌ {mercado}: {e}")

    lineas += ["\n─────────────────────", "_Reporte automático Buda.com_"]
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
