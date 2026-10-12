"""Translate insight text into the user's language with DeepSeek, keeping every number unchanged.

Safety: each translated title/body must contain exactly the numbers of the English source
(after normalising Bengali digits and separators). If not, the English text is kept.
"""
from __future__ import annotations

import json
import re

from app.agent.llm import DeepSeekClient, LLMUnavailable

LANG_NAMES = {"en": "English", "bn": "Bengali (Bangla script)", "zh": "Simplified Chinese"}
BN = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def numbers(text: str) -> list[str]:
    t = text.translate(BN).replace(",", "")
    return sorted(n.rstrip(".") for n in re.findall(r"\d+(?:\.\d+)?", t))


class Translator:
    def __init__(self, llm: DeepSeekClient | None):
        self.llm = llm
        self.cache: dict[tuple[str, str, str], dict] = {}

    def translate(self, insights: list[dict], lang: str) -> list[dict]:
        if lang == "en" or lang not in LANG_NAMES or self.llm is None or not insights:
            return insights
        todo = [i for i in insights if (i["id"], lang, i["body"]) not in self.cache]
        if todo:
            payload = {i["id"]: {"title": i["title"], "body": i["body"]} for i in todo}
            try:
                out = self.llm.chat_json([
                    {"role": "system", "content": (
                        f"Translate each item's title and body into {LANG_NAMES[lang]} for a student and their parent. "
                        "Keep every number, amount, date and currency symbol EXACTLY as in the source, using Western digits. "
                        "Keep it short and warm. Return json with the same keys: {\"<id>\": {\"title\": \"...\", \"body\": \"...\"}}.")},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ], max_tokens=1500)
            except LLMUnavailable:
                out = {}
            for i in todo:
                tr = out.get(i["id"]) if isinstance(out, dict) else None
                ok = (isinstance(tr, dict) and isinstance(tr.get("title"), str) and isinstance(tr.get("body"), str)
                      and numbers(tr["title"]) == numbers(i["title"]) and numbers(tr["body"]) == numbers(i["body"]))
                if ok:
                    self.cache[(i["id"], lang, i["body"])] = {"title": tr["title"], "body": tr["body"]}
        result = []
        for i in insights:
            tr = self.cache.get((i["id"], lang, i["body"]))
            result.append({**i, **tr, "translated": True} if tr else {**i, "translated": False})
        return result
