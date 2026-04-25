import os
import ccxt
import pytz
from datetime import datetime
from urllib.parse import quote
import requests

# ─── CONFIGURACIÓN ───────────────────────────────────────
TELEFONO        = os.environ["TELEFONO"]
APIKEY_BOT      = os.environ["APIKEY_BOT"]
BUDA_API_KEY    = os.environ["BUDA_API_KEY"]
BUDA_API_SECRET = os.environ["BUDA_API_SECRET"]
MERCADOS        = ["BTC/CLP", "ETH/CLP", "LTC/CLP", "USDC/CLP"]
# ─────────────────────────────────────────────────────────

def conectar_buda():
    return ccxt.buda({
        "apiKey": BUDA_API_KEY,
        "secret": BUDA_API_SECRET,
    })

def obtener_precio_compra_promedio(exchange, simbolo):
    """Obtiene precio promedio ponderado de las últimas compras ejecutadas"""
    try:
        ordenes = exchange.fetch_orders(simbolo, limit=20)
        compras = [o for o in ordenes if o["side"] == "buy" and o["status"] == "closed"]
        if not compras:
            return None, 0
        total_valor = sum(o["price"] * o["filled"] for o in compras if o["price"] and o["filled"])
        total_cantidad = sum(o["filled"] for o in compras if o["filled"])
        if total_cantidad == 0:
            return None, 0
        return total_valor / total_cantidad, len(compras)
    except Exception as e:
        print(f"Error obteniendo órdenes {simbolo}: {e}")
        return None, 0

def construir_mensaje(exchange):
    chile = pytz.timezone("America/Santiago")
    ahora = datetime.now(chile).strftime("%d/%m/%Y %H:%M")
    lineas = [
        f"🪙 *Reporte Cripto Buda.com*",
        f"📅 {ahora}",
        "─────────────────────",
    ]

    for simbolo in MERCADOS:
        try:
            ticker = exchange.fetch_ticker(simbolo)
            base   = simbolo.split("/")[0]
            precio_actual  = ticker["last"]
            variacion_24h  = ticker["percentage"] or 0
            bid            = ticker["bid"]
            ask            = ticker["ask"]
            emoji_24h      = "📈" if variacion_24h >= 0 else "📉"

            lineas += [
                f"\n*{base}*",
                f"  Precio : ${precio_actual:>15,.0f} CLP",
                f"  Compra : ${bid:>15,.0f}",
                f"  Venta  : ${ask:>15,.0f}",
                f"  24h    : {emoji_24h} {variacion_24h:+.2f}%",
            ]

            # Comparar con precio promedio de tus compras
            precio_compra, n_ordenes = obtener_precio_compra_promedio(exchange, simbolo)
            if precio_compra and precio_compra > 0:
                diff_pct = ((precio_actual - precio_compra) / precio_compra) * 100
                diff_clp = precio_actual - precio_compra
                emoji_diff = "🟢" if diff_pct >= 0 else "🔴"
                lineas += [
                    f"  ─────────────────",
                    f"  📊 Vs tus {n_ordenes} compras:",
                    f"  Precio prom : ${precio_compra:>12,.0f}",
                    f"  Diferencia  : {emoji_diff} {diff_pct:+.2f}% (${diff_clp:>+,.0f})",
                    f"  {'💡 Considera VENDER' if diff_pct >= 5 else '⏳ Mantener' if diff_pct >= 0 else '📉 En pérdida'}",
                ]
            else:
                lineas.append(f"  📊 Sin compras registradas")

        except Exception as e:
            lineas.append(f"\n❌ {simbolo}: {e}")

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
    exchange = conectar_buda()
    mensaje  = construir_mensaje(exchange)
    print(mensaje)
    enviar_whatsapp(mensaje)

if __name__ == "__main__":
    main()
