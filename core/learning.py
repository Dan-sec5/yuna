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
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.execute(
                """SELECT query_pattern, tool_name, success, count FROM lessons
                   WHERE query_pattern LIKE ? OR ? LIKE '%' || query_pattern || '%'
                   ORDER BY count DESC, timestamp DESC LIMIT ?""",
                (f"%{pattern}%", pattern, limit)
            )
            return [
                {"pattern": r[0], "tool": r[1], "success": bool(r[2]), "count": r[3]}
                for r in cur.fetchall()
            ]

    def get_best_tools_for(self, query: str) -> List[str]:
        lessons = self.get_lessons_for_query(query, limit=10)
        tool_scores = {}
        for l in lessons:
            if l["tool"] not in tool_scores:
                tool_scores[l["tool"]] = {"success": 0, "fail": 0}
            if l["success"]:
                tool_scores[l["tool"]]["success"] += l["count"]
            else:
                tool_scores[l["tool"]]["fail"] += l["count"]
        ranked = []
        for tool, scores in tool_scores.items():
            total = scores["success"] + scores["fail"]
            if total > 0:
                rate = scores["success"] / total
                ranked.append((tool, rate, total))
        ranked.sort(key=lambda x: (-x[1], -x[2]))
        return [t[0] for t in ranked[:3]]

    def _extract_pattern(self, query: str) -> str:
        stopwords = {"el", "la", "los", "las", "un", "una", "de", "en", "con", "por", "para", "que", "me", "mi", "yo"}
        words = [w.lower() for w in query.split() if len(w) > 3 and w.lower() not in stopwords]
        return " ".join(words[:3])
