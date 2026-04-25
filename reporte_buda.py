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

def generar_firma(method, path, nonce):
    # Formato correcto confirmado: "GET /path nonce"
    msg = f"{method} {path} {nonce}"
    return hmac.new(
        BUDA_API_SECRET.encode("utf-8"),
        msg.encode("utf-8"),
        hashlib.sha384
    ).hexdigest()

def request_privado(path, params=None):
    nonce  = str(int(time.time() * 1000))
    firma  = generar_firma("GET", path, nonce)
    headers = {
        "X-SBTC-APIKEY":    BUDA_API_KEY,
        "X-SBTC-NONCE":     nonce,
        "X-SBTC-SIGNATURE": firma,
    }
    r = requests.get(BASE_URL + path, headers=headers, params=params, timeout=10)
    print(f"[DEBUG] {path} -> {r.status_code}", flush=True)
    return r.json()

def obtener_ticker(mercado):
    r = requests.get(f"{BASE_URL}/markets/{mercado}/ticker", timeout=10)
    t = r.json()["ticker"]
    return {
        "precio":        float(t["last_price"][0]),
        "bid":           float(t["max_bid"][0]),
        "ask":           float(t["min_ask"][0]),
        "variacion_24h": float(t["price_variation_24h"]) * 100,
    }

def obtener_compras(mercado):
    # Endpoint correcto: /api/v2/orders (sin market en la URL)
    path = "/api/v2/orders"
    data = request_privado(path, params={
        "market_id": mercado,
        "state":     "traded",
        "per":       50,
        "page":      1
    })
    ordenes = data.get("orders", [])
    print(f"[DEBUG] {mercado}: {len(ordenes)} ordenes", flush=True)

    compras = []
    for o in ordenes:
        try:
            tipo   = str(o.get("order_type", "")).lower()
            estado = str(o.get("state", "")).lower()
            precio = float(o["price"][0]) if o.get("price") and o["price"][0] else None
            monto  = float(o["traded_amount"][0]) if o.get("traded_amount") and o["traded_amount"][0] else None
            print(f"  tipo={tipo} estado={estado} precio={precio} monto={monto}", flush=True)
            if "bid" in tipo and precio and monto and monto > 0:
                compras.append({"precio": precio, "monto": monto})
        except Exception as e:
            print(f"  error orden: {e}", flush=True)
    return compras

def precio_promedio(compras):
    if not compras:
        return None
    total_valor = sum(c["precio"] * c["monto"] for c in compras)
    total_monto = sum(c["monto"] for c in compras)
    return total_valor / total_monto if total_monto > 0 else None

def construir_mensaje():
    chile = pytz.timezone("America/Santiago")
    ahora = datetime.now(chile).strftime("%d/%m/%Y %H:%M")
    lineas = [
        "Reporte Cripto Buda.com",
        f"Fecha: {ahora}",
        "─────────────────────",
    ]

    for mercado in MERCADOS:
        try:
            t    = obtener_ticker(mercado)
            base = mercado.split("-")[0]
            signo = "+" if t["variacion_24h"] >= 0 else ""
            lineas += [
                f"\n{base}",
                f"  Precio : ${t['precio']:>15,.0f} CLP",
                f"  Compra : ${t['bid']:>15,.0f}",
                f"  Venta  : ${t['ask']:>15,.0f}",
                f"  24h    : {signo}{t['variacion_24h']:.2f}%",
            ]

            compras = obtener_compras(mercado)
            prom    = precio_promedio(compras)

            if prom:
                diff_pct = ((t["precio"] - prom) / prom) * 100
                diff_clp = t["precio"] - prom
                signo_d  = "+" if diff_pct >= 0 else ""
                decision = "CONSIDERA VENDER" if diff_pct >= 5 else "Mantener" if diff_pct >= 0 else "En perdida"
                lineas += [
                    f"  ─────────────────",
                    f"  Vs tus {len(compras)} compras:",
                    f"  Prom compra : ${prom:>12,.0f}",
                    f"  Diferencia  : {signo_d}{diff_pct:.2f}% (${diff_clp:>+,.0f})",
                    f"  {decision}",
                ]
            else:
                lineas.append("  Sin compras ejecutadas")

        except Exception as e:
            lineas.append(f"\nError {mercado}: {e}")

    lineas += ["\n─────────────────────", "Reporte automatico Buda.com"]
    return "\n".join(lineas)

def enviar_whatsapp(mensaje):
    url = f"https://api.callmebot.com/whatsapp.php?phone={TELEFONO}&text={quote(mensaje)}&apikey={APIKEY_BOT}"
    r = requests.get(url, timeout=15)
    print("WhatsApp enviado OK" if r.status_code == 200 else f"Error WhatsApp: {r.status_code}", flush=True)

def main():
    mensaje = construir_mensaje()
    print(mensaje, flush=True)
    enviar_whatsapp(mensaje)

if __name__ == "__main__":
    main()
