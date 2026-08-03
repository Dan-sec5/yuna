"""
core/learning.py — Sistema de auto-mejora de Yuna
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from config import get

DB_PATH = Path(get("paths.memory_db", "~/yuna/data/yuna.db")).expanduser()

class LearningEngine:
    def __init__(self):
        self._init_tables()

    def _init_tables(self):
        with sqlite3.connect(DB_PATH) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS lessons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    query_pattern TEXT,
                    tool_name TEXT,
                    outcome TEXT,
                    success BOOLEAN,
                    count INTEGER DEFAULT 1
                );
                CREATE INDEX IF NOT EXISTS idx_lessons_pattern ON lessons(query_pattern);
                CREATE INDEX IF NOT EXISTS idx_lessons_tool ON lessons(tool_name);
                CREATE TABLE IF NOT EXISTS user_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    query TEXT,
                    response TEXT,
                    feedback TEXT,
                    score INTEGER
                );
                CREATE TABLE IF NOT EXISTS interaction_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    query TEXT,
                    response TEXT,
                    tools_used TEXT,
                    success BOOLEAN,
                    latency_ms REAL
                );
            """)

    def _normalize_learning_words(self, pattern: str) -> set:
        """
        Normaliza palabras para que pequeñas variaciones
        no rompan el aprendizaje.

        Ejemplos:
        busca    -> buscar
        encuentra -> buscar
        localiza  -> buscar
        archivos  -> archivo
        documentos -> archivo
        downloads -> descargas
        """
        equivalencias = {
            "busca": "buscar",
            "buscar": "buscar",
            "encuentra": "buscar",
            "encontrar": "buscar",
            "localiza": "buscar",
            "localizar": "buscar",
            "archivo": "archivo",
            "archivos": "archivo",
            "documento": "archivo",
            "documentos": "archivo",
            "downloads": "descargas",
        }

        resultado = set()

        for palabra in pattern.split():
            resultado.add(
                equivalencias.get(palabra, palabra)
            )

        return resultado

    def record_lesson(self, query: str, tool_name: str, outcome: str, success: bool):
        pattern = self._extract_pattern(query)
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.execute(
                "SELECT id, count FROM lessons WHERE query_pattern = ? AND tool_name = ? AND success = ?",
                (pattern, tool_name, success)
            )
            row = cur.fetchone()
            if row:
                conn.execute(
                    "UPDATE lessons SET count = count + 1, timestamp = CURRENT_TIMESTAMP WHERE id = ?",
                    (row[0],)
                )
            else:
                conn.execute(
                    "INSERT INTO lessons (query_pattern, tool_name, outcome, success) VALUES (?, ?, ?, ?)",
                    (pattern, tool_name, outcome, success)
                )

    def record_user_feedback(self, query: str, feedback: str, response: str = ""):
        score = 1 if feedback in ("up", "positive", "👍", "bueno", "util") else -1
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO user_feedback (query, response, feedback, score) VALUES (?, ?, ?, ?)",
                (query[:500], response[:500], feedback, score)
            )

    def get_lessons_for_query(self, query: str, limit: int = 3) -> List[Dict]:
        pattern = self._extract_pattern(query)

        if not pattern:
            return []

        query_words = self._normalize_learning_words(pattern)

        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.execute(
                """
                SELECT query_pattern, tool_name, success, count, timestamp
                FROM lessons
                """
            )

            candidatos = []

            for row in cur.fetchall():
                saved_pattern = row[0] or ""
                saved_words = self._normalize_learning_words(saved_pattern)

                if not saved_words:
                    continue

                # Coincidencia por palabras compartidas.
                comunes = query_words & saved_words

                if not comunes:
                    continue

                # Porcentaje de coincidencia respecto al patrón
                # más pequeño. Esto permite que:
                # "archivo descargas"
                # coincida con:
                # "buscar archivo descargas"
                base = min(len(query_words), len(saved_words))
                score = len(comunes) / base

                # Exigimos al menos una coincidencia fuerte.
                if score >= 0.5:
                    candidatos.append({
                        "pattern": saved_pattern,
                        "tool": row[1],
                        "success": bool(row[2]),
                        "count": row[3],
                        "score": score,
                        "timestamp": row[4],
                    })

            candidatos.sort(
                key=lambda x: (
                    -x["score"],
                    -x["count"],
                )
            )

            return [
                {
                    "pattern": x["pattern"],
                    "tool": x["tool"],
                    "success": x["success"],
                    "count": x["count"],
                }
                for x in candidatos[:limit]
            ]

    def get_best_tools_for(self, query: str) -> List[str]:
        """
        Devuelve las herramientas más adecuadas para una consulta.

        El ranking combina:
        - similitud del patrón
        - tasa histórica de éxito
        - cantidad de experiencias
        """

        pattern = self._extract_pattern(query)

        if not pattern:
            return []

        query_words = self._normalize_learning_words(pattern)

        lessons = self.get_lessons_for_query(query, limit=20)

        if not lessons:
            return []

        tool_scores = {}

        for lesson in lessons:
            tool = lesson["tool"]
            success = lesson["success"]
            count = lesson["count"]

            saved_pattern = lesson["pattern"]
            saved_words = self._normalize_learning_words(
                self._extract_pattern(saved_pattern)
            )

            if not saved_words:
                continue

            comunes = query_words & saved_words

            if not comunes:
                continue

            similarity = len(comunes) / max(
                len(query_words),
                len(saved_words)
            )

            if tool not in tool_scores:
                tool_scores[tool] = {
                    "success": 0,
                    "fail": 0,
                    "similarity": 0.0,
                    "experience": 0,
                }

            if success:
                tool_scores[tool]["success"] += count
            else:
                tool_scores[tool]["fail"] += count

            tool_scores[tool]["similarity"] = max(
                tool_scores[tool]["similarity"],
                similarity
            )

            tool_scores[tool]["experience"] += count

        ranked = []

        for tool, data in tool_scores.items():
            total = data["success"] + data["fail"]

            if total == 0:
                continue

            success_rate = data["success"] / total

            # No recomendar herramientas que nunca han tenido éxito.
            if data["success"] == 0:
                continue

            # Ranking combinado.
            final_score = (
                data["similarity"] * 0.50
                + success_rate * 0.40
                + min(data["experience"], 10) / 10 * 0.10
            )

            ranked.append(
                (
                    tool,
                    final_score,
                    success_rate,
                    data["similarity"],
                    data["experience"],
                )
            )

        ranked.sort(
            key=lambda x: (
                -x[1],
                -x[2],
                -x[3],
                -x[4],
            )
        )

        return [item[0] for item in ranked[:3]]

    def _extract_pattern(self, query: str) -> str:
        import re
        import unicodedata

        if not query:
            return ""

        # Normalizar minúsculas y acentos
        text = unicodedata.normalize("NFD", query.lower())
        text = "".join(
            c for c in text
            if unicodedata.category(c) != "Mn"
        )

        # Eliminar puntuación
        text = re.sub(r"[¿?!¡,.;:]", " ", text)

        # Normalizar palabras equivalentes
        replacements = {
            "busca": "buscar",
            "buscame": "buscar",
            "encuentra": "buscar",
            "encontrar": "buscar",
            "localiza": "buscar",
            "localizar": "buscar",
            "archivos": "archivo",
            "documentos": "archivo",
            "downloads": "descargas",
            "download": "descargas",
        }

        stopwords = {
            "el", "la", "los", "las",
            "un", "una", "de", "del",
            "en", "con", "por", "para",
            "que", "hay",
            "me", "mi", "yo",
            "tengo",
        }

        words = []

        for word in text.split():
            if word in stopwords:
                continue

            word = replacements.get(word, word)

            if len(word) > 2:
                words.append(word)

        # Eliminar duplicados conservando orden
        result = []

        for word in words:
            if word not in result:
                result.append(word)

        return " ".join(result[:4])
