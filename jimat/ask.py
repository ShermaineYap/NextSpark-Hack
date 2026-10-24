"""Tiny rule-based parser so people can type what they'd say to a friend:
"RM60 for 2 people, 5 days, no beef" / "RM40 2 orang 3 hari vegetarian".
No LLM, no API key — works offline."""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Ask:
    budget: float | None = None
    people: int | None = None
    days: int | None = None
    meals_per_day: int | None = None
    exclusions: list[str] = field(default_factory=list)


_NUM = r"(\d+(?:\.\d+)?)"


def parse(text: str) -> Ask:
    t = text.lower()
    a = Ask()
    m = re.search(r"rm\s*" + _NUM, t) or re.search(_NUM + r"\s*(?:ringgit|rm)", t)
    if m:
        a.budget = float(m.group(1))
    m = re.search(_NUM + r"\s*(?:people|person|pax|orang|org|ppl|of us)", t)
    if m:
        a.people = int(float(m.group(1)))
    elif re.search(r"\b(?:me|myself|alone|solo|seorang)\b", t):
        a.people = 1
    m = re.search(_NUM + r"\s*(?:days?|hari)", t)
    if m:
        a.days = int(float(m.group(1)))
    elif re.search(r"\b(?:week|minggu|seminggu)\b", t):
        a.days = 7
    elif re.search(r"\bweekend\b", t):
        a.days = 2
    m = re.search(_NUM + r"\s*meals?\s*(?:a|per|/)\s*day", t)
    if m:
        a.meals_per_day = int(float(m.group(1)))
    elif re.search(r"\b(?:dinner only|dinners? only|makan malam saja)\b", t):
        a.meals_per_day = 1

    rules = {
        "No beef": r"\b(?:no|tak|tiada|without|skip)\s*(?:beef|daging|lembu)\b|\bno red meat\b",
        "No mutton": r"\b(?:no|tak|tiada|without|skip)\s*(?:mutton|kambing|lamb)\b|\bno red meat\b",
        "No chicken": r"\b(?:no|tak|tiada|without|skip)\s*(?:chicken|ayam)\b",
        "No seafood (fish, prawn, squid)": r"\b(?:no|tak|tiada|without|skip)\s*(?:seafood|fish|ikan|prawn|udang|squid|sotong)\b",
        "Vegetarian only": r"\b(?:vegetarian|vegan|veggie|sayur\s*(?:saja|sahaja|only))\b",
        "Quick meals only (≤ 25 min)": r"\b(?:quick|fast|cepat|busy|no time|simple)\b",
    }
    for name, pat in rules.items():
        if re.search(pat, t):
            a.exclusions.append(name)
    return a
