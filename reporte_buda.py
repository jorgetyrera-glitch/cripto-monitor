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
    # La firma usa solo el path, sin query params
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

def obtener_ultima_compra(mercado):
    nonce  = str(int(time.time() * 1000))
    params_str = f"market_id={mercado}&state=traded&per=50&page=1"
    path_con_params = f"/api/v2/orders?{params_str}"
    msg   = f"GET {path_con_params} {nonce}"
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
    r = requests.get("https://www.buda.com/api/v2/orders", headers=headers, params={
        "market_id": mercado,
        "state":     "traded",
        "per":       50,
        "page":      1
    }, timeout=10)

    data    = r.json()
    ordenes = data.get("orders", [])

    # Buscar la compra (Bid) más reciente del mercado correcto
    for o in ordenes:
        tipo = str(o.get("type", "")).strip()
        mkt  = str(o.get("market_id", "")).strip()
        if tipo != "Bid" or mkt != mercado:
            continue
        try:
            total_clp = o.get("total_exchanged")
            cantidad  = o.get("traded_amount")
            fecha     = o.get("created_at", "")[:10]
            if not total_clp or not cantidad:
                continue
            clp  = float(total_clp[0])
            btc  = float(cantidad[0])
            if btc <= 0 or clp <= 0:
                continue
            precio_compra = clp / btc
            print(f"[DEBUG] {mercado} ultima compra: ${precio_compra:,.0f} ({fecha})", flush=True)
            return precio_compra, fecha
        except Exception as e:
            print(f"[DEBUG] error: {e}", flush=True)
            continue

    return None, None
    
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
        f"Reporte Cripto Buda.com",
        f"Fecha: {ahora}",
        "─────────────────",
    ]

    for mercado in MERCADOS:
        try:
            t    = obtener_ticker(mercado)
            base = mercado.split("-")[0]
            signo_24h = "+" if t["variacion_24h"] >= 0 else ""

            precio_compra, fecha_compra = obtener_ultima_compra(mercado)

            if precio_compra:
                diff_pct = (t["precio"] - precio_compra) * 100 / precio_compra
                signo    = "+" if diff_pct >= 0 else ""

                if diff_pct >= 5:
                    decision = "VENDER"
                elif diff_pct >= 0:
                    decision = "Mantener (ganancia)"
                elif diff_pct >= -5:
                    decision = "Mantener (leve perdida)"
                else:
                    decision = "Mantener (esperar)"

                lineas += [
                    f"\n{base}: ${t['precio']:,.0f}",
                    f"  24h: {signo_24h}{t['variacion_24h']:.2f}%",
                    f"  Compra {fecha_compra}: ${precio_compra:,.0f}",
                    f"  Variacion: {signo}{diff_pct:.2f}%",
                    f"  {decision}",
                ]
            else:
                lineas += [
                    f"\n{base}: ${t['precio']:,.0f}",
                    f"  24h: {signo_24h}{t['variacion_24h']:.2f}%",
                    f"  Sin compras ejecutadas",
                ]

        except Exception as e:
            lineas.append(f"\nError {mercado}: {e}")

    lineas += ["\n─────────────────", "Buda.com"]
    return "\n".join(lineas)

def enviar_whatsapp(mensaje):
    url = "https://api.callmebot.com/whatsapp.php"
    params = {
        "phone":  TELEFONO,
        "text":   mensaje,
        "apikey": APIKEY_BOT,
    }
    r = requests.get(url, params=params, timeout=15)
    print("WhatsApp enviado OK" if r.status_code == 200 else f"Error: {r.status_code}", flush=True)

def main():
    mensaje = construir_mensaje()
    print(mensaje, flush=True)
    enviar_whatsapp(mensaje)

if __name__ == "__main__":
    main()
