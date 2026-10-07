from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Callable, Any


ALLOWED_ACTIONS = {
    "inspect_workspace",
    "git_status",
    "list_tests",
    "read_file",
    "search_files",
    "run_tests",
    "run_safe_command",
    "edit_file",
    "create_file",
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

            decision = self._avoid_repetition(
                decision=decision,
                snapshot=snapshot,
                recent_history=history,
            )

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

        # Contexto deliberadamente pequeño para modelos locales.
        # El planner decide UNA acción, no necesita tragarse
        # todo el proyecto en cada iteración.
        prompt_snapshot = {
            "workspace": snapshot.get(
                "workspace",
                "",
            ),
            "top_level": snapshot.get(
                "top_level",
                [],
            )[:35],
            "tests": snapshot.get(
                "tests",
                [],
            )[:20],
            "git_status": str(
                snapshot.get(
                    "git_status",
                    "",
                )
            )[:1500],
        }

        compact_snapshot = json.dumps(
            prompt_snapshot,
            ensure_ascii=False,
            separators=(",", ":"),
        )

        compact_history = "\n---\n".join(
            entry[:800]
            for entry in recent_history[-3:]
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
- read_file
- search_files
- run_tests
- run_safe_command
- edit_file
- create_file
- finish

USO DE target:
- read_file:
  target debe ser una ruta relativa, por ejemplo:
  "core/agent.py"

- search_files:
  target debe ser texto o símbolo a buscar, por ejemplo:
  "AvatarResolver"

- run_tests:
  target puede estar vacío para toda la suite
  o ser una ruta como:
  "tests/test_agent.py"

- run_safe_command:
  target debe ser un comando diagnóstico de solo lectura,
  por ejemplo:
  "git diff --stat"

- edit_file:
  target debe contener:
  RUTA ||| CONTENIDO_COMPLETO

  ejemplo:
  core/example.py ||| VALUE = 42

- create_file:
  target debe contener:
  RUTA ||| CONTENIDO_COMPLETO

  ejemplo:
  notes/example.txt ||| contenido

- inspect_workspace, git_status, list_tests y finish:
  target debe quedar vacío

REGLAS:
1. Elige solamente una acción.
2. No inventes archivos.
3. No propongas borrar ni modificar nada.
4. Lee cuidadosamente RESULT de los pasos anteriores.
5. No repitas una acción que ya produjo información suficiente.
6. Después de list_tests, normalmente lee o busca archivos relevantes.
7. Después de run_tests exitoso, investiga código o termina.
8. Usa finish solamente cuando ya exista suficiente inspección.
9. Si RESULT contiene NO_CHANGE, no repitas la misma edición.
10. Si el archivo ya cumple la intención de la subtarea, continúa o usa finish.
11. Responde únicamente JSON válido.

REGLAS DE BÚSQUEDA:
- Para search_files usa nombres de clases, funciones,
  símbolos o fragmentos técnicos.
- Prefiere "ProjectRunner", "ProjectWorker", "project_"
  en vez de frases vagas como "Project Mode".
- Si una búsqueda no devuelve resultados, cambia el target.
- Nunca leas dos veces el mismo archivo sin una razón nueva.

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
            num_predict=180,
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

        raw_target = str(
            data.get("target", "")
        )

        # edit_file/create_file transportan contenido completo.
        # No debemos usar strip(), porque eliminaría saltos
        # de línea significativos al final del archivo.
        if action in {
            "edit_file",
            "create_file",
        }:
            target = raw_target.strip(
                " \t\r"
            )
        else:
            target = raw_target.strip()

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

    def _avoid_repetition(
        self,
        *,
        decision: ProjectDecision,
        snapshot: dict[str, Any],
        recent_history: list[str],
    ) -> ProjectDecision:

        if not recent_history:
            return decision

        recent_actions = []

        for entry in recent_history[-3:]:
            match = re.search(
                r"ACTION=([a-z_]+)",
                entry,
            )

            if match:
                recent_actions.append(
                    match.group(1)
                )

        if not recent_actions:
            return decision

        # Una repetición puede ser válida.
        # Dos consecutivas iguales ya requieren intervención.
        if (
            len(recent_actions) >= 2
            and recent_actions[-1] == decision.action
            and recent_actions[-2] == decision.action
        ):
            alternatives = [
                "inspect_workspace",
                "git_status",
                "list_tests",
                "search_files",
                "read_file",
                "run_tests",
                "finish",
            ]

            for action in alternatives:
                if action not in recent_actions[-2:]:
                    if action == "search_files":
                        return ProjectDecision(
                            action="search_files",
                            reason=(
                                "Evitar repetición y localizar "
                                "código relacionado con Project Mode."
                            ),
                            target="Project",
                        )

                    if action == "read_file":
                        continue

                    return ProjectDecision(
                        action=action,
                        reason=(
                            "Acción alternativa seleccionada "
                            "para evitar un bucle."
                        ),
                        target="",
                    )

            return ProjectDecision(
                action="finish",
                reason=(
                    "Se detectó repetición persistente "
                    "sin progreso."
                ),
            )

        return decision

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
