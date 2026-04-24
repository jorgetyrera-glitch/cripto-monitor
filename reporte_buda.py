import requests
from datetime import datetime
import pytz
from urllib.parse import quote

# ─── CONFIGURACIÓN ───────────────────────────────────────
import os
TELEFONO   = os.environ["TELEFONO"]       # Se leerá desde variables secretas
APIKEY_BOT = os.environ["APIKEY_BOT"]
MERCADOS   = ["BTC-CLP", "ETH-CLP", "LTC-CLP", "USDC-CLP"]
# ─────────────────────────────────────────────────────────

BASE_URL = "https://www.buda.com/api/v2"

def obtener_ticker(mercado):
    url = f"{BASE_URL}/markets/{mercado}/ticker"
    r = requests.get(url, timeout=10)
    t = r.json()["ticker"]
    return {
        "mercado":      mercado,
        "precio":       float(t["last_price"][0]),
        "bid":          float(t["max_bid"][0]),
        "ask":          float(t["min_ask"][0]),
        "variacion_24h": float(t["price_variation_24h"]) * 100,
    }

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
    chile = pytz.timezone("America/Santiago")
    ahora = datetime.now(chile).strftime("%d/%m/%Y %H:%M")
    lineas = [f"🪙 *Reporte Cripto Buda.com*", f"📅 {ahora}", "─────────────────────"]

    for mercado in MERCADOS:
        try:
            t = obtener_ticker(mercado)
            emoji = "📈" if t["variacion_24h"] >= 0 else "📉"
            base = mercado.split("-")[0]
            lineas += [
                f"\n*{base}*",
                f"  Precio : ${t['precio']:>15,.0f} CLP",
                f"  Compra : ${t['bid']:>15,.0f}",
                f"  Venta  : ${t['ask']:>15,.0f}",
                f"  24h    : {emoji} {t['variacion_24h']:+.2f}%",
            ]
        except Exception as e:
            lineas.append(f"\n❌ {mercado}: error")

    lineas += ["─────────────────────", "_Reporte automático desde Buda.com_"]
    mensaje = "\n".join(lineas)
    print(mensaje)
    enviar_whatsapp(mensaje)

if __name__ == "__main__":
    main()
