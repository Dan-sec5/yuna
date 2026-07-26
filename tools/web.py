import yfinance as yf
from ddgs import DDGS
from datetime import datetime

def buscar_web(query, max_resultados=3):
    """Busca en DuckDuckGo sin API key"""
    try:
        with DDGS() as ddgs:
            resultados = list(ddgs.text(query, max_results=max_resultados))
        resumen = []
        for r in resultados:
            resumen.append(f"• {r['title']}")
            resumen.append(f"  {r['body'][:200]}")
        return "\n".join(resumen)
    except Exception as e:
        return f"Error en búsqueda: {e}"

def precio_activo(ticker):
    """Obtiene precio actual de un activo financiero"""
    try:
        activo = yf.Ticker(ticker)
        hist = activo.history(period="5d")
        if hist.empty:
            return f"No se encontró información para {ticker}"

        precios = hist['Close'].dropna()
        if precios.empty:
            return f"No hay precios disponibles para {ticker}"

        precio_actual = precios.iloc[-1]
        precio_anterior = precios.iloc[-2] if len(precios) > 1 else None

        # Detectar si mercado está cerrado
        hoy = datetime.now()
        es_fin_semana = hoy.weekday() >= 5
        nota = " (mercado cerrado — fin de semana)" if es_fin_semana else ""

        if precio_anterior:
            cambio = precio_actual - precio_anterior
            cambio_pct = (cambio / precio_anterior) * 100
            signo = "↑" if cambio >= 0 else "↓"
            return (
                f"📈 {ticker.upper()}{nota}\n"
                f"Último precio: ${precio_actual:.2f}\n"
                f"Cambio: {signo} {abs(cambio):.2f} ({abs(cambio_pct):.2f}%)\n"
                f"Precio anterior: ${precio_anterior:.2f}"
            )
        else:
            return f"📈 {ticker.upper()}{nota}\nÚltimo precio: ${precio_actual:.2f}"
    except Exception as e:
        return f"Error obteniendo precio de {ticker}: {e}"

def noticias_financieras_mx(max_resultados=3):
    """Busca noticias financieras relevantes para México"""
    return buscar_web("fideicomisos Mexico finanzas noticias hoy", max_resultados)
