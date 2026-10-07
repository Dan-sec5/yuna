from __future__ import annotations

import json
import re
from typing import Callable

from core.project_plan import ProjectPlan


class ProjectPlanBuilder:
    """
    Genera un plan inicial compacto.
    Una sola llamada al LLM por sesión.
    """

    def __init__(
        self,
        llm_call: Callable[[str], str] | None = None,
    ) -> None:
        self.llm_call = llm_call

    def build(
        self,
        *,
        objective: str,
        workspace_summary: str,
        max_tasks: int = 6,
    ) -> ProjectPlan:

        prompt = f"""
Eres el planificador inicial de Yuna Project Mode.

OBJETIVO:
{objective}

WORKSPACE:
{workspace_summary}

Crea un plan corto, concreto y ejecutable.

REGLAS:
- Entre 3 y {max_tasks} tareas.
- Cada tarea debe producir progreso real.
- Evita tareas redundantes.
- Incluye verificación final.
- No inventes archivos concretos si aún no fueron inspeccionados.
- Responde únicamente JSON válido.

FORMATO:
{{
  "tasks": [
    {{
      "title": "Inspeccionar el proyecto",
      "description": "Entender estructura y estado actual"
    }}
  ]
}}
""".strip()

        try:
            raw = (
                self.llm_call(prompt)
                if self.llm_call
                else self._call_local_model(prompt)
            )

            tasks = self._parse(raw)

        except Exception:
            tasks = self._fallback()

        plan = ProjectPlan.new(
            objective
        )

        for item in tasks[:max_tasks]:
            plan.add_task(
                item["title"],
                item.get(
                    "description",
                    "",
                ),
            )

        return plan

    def _call_local_model(
        self,
        prompt: str,
    ) -> str:

        from core.llm import (
            chat_simple,
            clean_response,
        )

        response = chat_simple(
            [
                {
                    "role": "system",
                    "content": (
                        "Eres un planificador técnico. "
                        "Responde solo JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.2,
            num_predict=320,
        )

        return clean_response(
            response
        )

    def _parse(
        self,
        raw: str,
    ) -> list[dict]:

        raw = raw.strip()

        try:
            data = json.loads(raw)

        except json.JSONDecodeError:
            match = re.search(
                r"\{.*\}",
                raw,
                flags=re.DOTALL,
            )

            if not match:
                raise ValueError(
                    "Plan sin JSON."
                )

            data = json.loads(
                match.group(0)
            )

        tasks = data.get(
            "tasks",
            []
        )

        if not isinstance(
            tasks,
            list,
        ):
            raise ValueError(
                "tasks inválido."
            )

        cleaned = []

        for item in tasks:

            if not isinstance(
                item,
                dict,
            ):
                continue

            title = str(
                item.get(
                    "title",
                    "",
                )
            ).strip()

            if not title:
                continue

            cleaned.append({
                "title": title,
                "description": str(
                    item.get(
                        "description",
                        "",
                    )
                ).strip(),
            })

        if len(cleaned) < 2:
            raise ValueError(
                "Plan demasiado corto."
            )

        return cleaned

    @staticmethod
    def _fallback() -> list[dict]:
        return [
            {
                "title": "Inspeccionar el proyecto",
                "description": (
                    "Revisar estructura, Git y archivos relevantes."
                ),
            },
            {
                "title": "Ejecutar verificaciones iniciales",
                "description": (
                    "Ejecutar tests relevantes y detectar fallos."
                ),
            },
            {
                "title": "Investigar el problema",
                "description": (
                    "Leer código y localizar la causa."
                ),
            },
            {
                "title": "Aplicar cambios necesarios",
                "description": (
                    "Realizar cambios mínimos y seguros."
                ),
            },
            {
                "title": "Verificar resultado final",
                "description": (
                    "Comprobar tests y estado del proyecto."
                ),
            },
        ]
