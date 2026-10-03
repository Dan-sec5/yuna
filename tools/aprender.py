import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/yuna"))

from config import get
from core.llm import chat_simple, clean_response
from memory.manager import (
    DB_PATH,
    get_all_preferencias,
    get_episodic,
    set_preferencia,
)


MODEL_AGENT = get("models.agent", "maid:latest")


def main():
    if not DB_PATH.exists():
        print("No hay base de datos. Usa Yuna primero.")
        return

    preferencias = get_all_preferencias()
    episodic = get_episodic(100)

    if not episodic:
        print("No hay suficientes datos para analizar.")
        return

    # ---------------------------------------------------------
    # Construir resumen de actividad
    # ---------------------------------------------------------

    bitacora_resumen = []

    for evento in episodic:
        detalles = evento.get("detalles", "{}")

        try:
            datos = json.loads(detalles)

            texto_usuario = datos.get(
                "user",
                evento.get("evento", "")
            )

        except (json.JSONDecodeError, TypeError):
            texto_usuario = evento.get("evento", "")

        fecha = evento.get("fecha", "sin fecha")

        bitacora_resumen.append(
            f"- {fecha}: {texto_usuario}"
        )

    # ---------------------------------------------------------
    # Preferencias conocidas
    # ---------------------------------------------------------

    preferencias_resumen = []

    if isinstance(preferencias, dict):
        for clave, valor in list(preferencias.items())[:30]:
            preferencias_resumen.append(
                f"- {clave}: {valor}"
            )

    elif preferencias:
        preferencias_resumen.append(str(preferencias)[:3000])

    contexto_preferencias = (
        "\n".join(preferencias_resumen)
        if preferencias_resumen
        else "Sin preferencias registradas."
    )

    # ---------------------------------------------------------
    # Prompt de aprendizaje
    # ---------------------------------------------------------

    prompt = f"""
Analiza el historial de uso de Yuna.

Identifica:

1. Las tareas que Luis realiza con mayor frecuencia.
2. Los temas que consulta habitualmente.
3. Herramientas de Yuna que parecen ser más útiles.
4. Patrones recurrentes de trabajo.
5. Automatizaciones que podrían ser útiles.
6. Preferencias relevantes que puedan mejorar futuras respuestas.

No inventes información.
Utiliza únicamente los datos proporcionados.

PREFERENCIAS CONOCIDAS:

{contexto_preferencias}


HISTORIAL RECIENTE:

{chr(10).join(bitacora_resumen[:50])}


Responde en español.
Sé conciso y estructurado.
""".strip()

    print("🧠 Analizando tus actividades...")

    respuesta = chat_simple(
        [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model=MODEL_AGENT,
        num_predict=500,
        temperature=0.3,
    )

    patrones = clean_response(respuesta)

    if not patrones:
        patrones = "No se pudo generar el análisis."

    print(
        f"\n📊 Patrones detectados:\n"
        f"{patrones}\n"
    )

    # ---------------------------------------------------------
    # Guardar aprendizaje
    # ---------------------------------------------------------

    fecha = datetime.now().strftime("%Y-%m-%d")

    set_preferencia(
        f"patrones_{fecha}",
        patrones[:2000],
    )

    print(
        "✓ Memoria actualizada con los patrones de uso."
    )


if __name__ == "__main__":
    main()
