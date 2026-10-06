from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Callable, Any


ALLOWED_ACTIONS = {
    "inspect_workspace",
    "git_status",
    "list_tests",
    "finish",
}


@dataclass(frozen=True)
class ProjectDecision:
    action: str
    reason: str
    target: str = ""

    def __post_init__(self):
        if self.action not in ALLOWED_ACTIONS:
            raise ValueError(
                f"Acción no permitida: {self.action}"
            )


class ProjectPlanner:
    """
    Planner ligero para Project Mode.

    El LLM solamente DECIDE.
    No ejecuta herramientas directamente.
    """

    def __init__(
        self,
        llm_call: Callable[[str], str] | None = None,
    ) -> None:
        self.llm_call = llm_call

    def plan(
        self,
        *,
        objective: str,
        step: int,
        max_steps: int,
        remaining_seconds: float,
        snapshot: dict[str, Any],
        recent_history: list[str] | None = None,
    ) -> ProjectDecision:

        history = recent_history or []

        prompt = self._build_prompt(
            objective=objective,
            step=step,
            max_steps=max_steps,
            remaining_seconds=remaining_seconds,
            snapshot=snapshot,
            recent_history=history,
        )

        try:
            if self.llm_call is not None:
                raw = self.llm_call(prompt)
            else:
                raw = self._call_local_model(prompt)

            decision = self._parse_decision(raw)

            return decision

        except Exception:
            # Nunca dejamos caer Project Mode
            # por un problema de formato del modelo.
            return self._fallback(
                step=step,
                snapshot=snapshot,
                recent_history=history,
            )

    def _build_prompt(
        self,
        *,
        objective: str,
        step: int,
        max_steps: int,
        remaining_seconds: float,
        snapshot: dict[str, Any],
        recent_history: list[str],
    ) -> str:

        compact_snapshot = json.dumps(
            snapshot,
            ensure_ascii=False,
            indent=2,
        )

        compact_history = "\n".join(
            recent_history[-5:]
        )

        return f"""
Eres el planner de Yuna Project Mode.

Tu trabajo NO es ejecutar comandos.
Tu trabajo es elegir UNA sola acción siguiente.

OBJETIVO:
{objective}

PROGRESO:
Paso {step}/{max_steps}
Tiempo restante: {int(remaining_seconds)} segundos

HISTORIAL RECIENTE:
{compact_history or "Sin pasos previos"}

ESTADO DEL PROYECTO:
{compact_snapshot}

ACCIONES PERMITIDAS:
- inspect_workspace
- git_status
- list_tests
- finish

REGLAS:
1. Elige solamente una acción.
2. No inventes archivos.
3. No propongas borrar ni modificar nada.
4. Evita repetir una acción sin necesidad.
5. Usa finish solamente cuando ya exista suficiente inspección.
6. Responde únicamente JSON válido.

FORMATO EXACTO:
{{
  "action": "inspect_workspace",
  "reason": "Motivo breve",
  "target": ""
}}
""".strip()

    def _call_local_model(
        self,
        prompt: str,
    ) -> str:
        from core.llm import (
            chat_simple,
            clean_response,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "Eres un planificador técnico preciso. "
                    "Responde exclusivamente JSON."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]

        response = chat_simple(
            messages,
            temperature=0.2,
            num_predict=300,
        )

        return clean_response(response)

    def _parse_decision(
        self,
        raw: str,
    ) -> ProjectDecision:

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
                    "El modelo no devolvió JSON."
                )

            data = json.loads(
                match.group(0)
            )

        action = str(
            data.get("action", "")
        ).strip()

        reason = str(
            data.get("reason", "")
        ).strip()

        target = str(
            data.get("target", "")
        ).strip()

        if action not in ALLOWED_ACTIONS:
            raise ValueError(
                f"Acción inválida: {action}"
            )

        if not reason:
            reason = "Sin motivo especificado."

        return ProjectDecision(
            action=action,
            reason=reason,
            target=target,
        )

    def _fallback(
        self,
        *,
        step: int,
        snapshot: dict[str, Any],
        recent_history: list[str],
    ) -> ProjectDecision:

        joined = " ".join(
            recent_history
        ).lower()

        if step == 0:
            return ProjectDecision(
                action="inspect_workspace",
                reason="Inspección inicial del proyecto.",
            )

        if "git_status" not in joined:
            return ProjectDecision(
                action="git_status",
                reason="Revisar cambios actuales del repositorio.",
            )

        if (
            snapshot.get("tests")
            and "list_tests" not in joined
        ):
            return ProjectDecision(
                action="list_tests",
                reason="Identificar pruebas disponibles.",
            )

        return ProjectDecision(
            action="finish",
            reason="Inspección inicial suficiente.",
        )
