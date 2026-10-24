"""Price engine: turn the raw PriceCatcher snapshot into
"what does ingredient X cost near me today, and is it getting worse?"
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"

# How many days of recent observations count as "current" for a premise.
RECENT_DAYS = 14
# Trend window: compare the last 7 days against the 30 days before that.
TREND_NOW_DAYS = 7
TREND_BASE_DAYS = 30


@dataclass(frozen=True)
class UnitSpec:
    size: float   # how many base units one priced unit contains
    base: str     # "kg", "g", "ml", "biji", "pack"


def parse_unit(unit: str) -> UnitSpec:
    """'1kg' -> 1 kg; '30 biji' -> 30 biji; '345ml' -> 345 ml; '10 kg' -> 10 kg;
    '5 X 79g' -> 5 pack; '+- 500g' -> 500 g; '1 liter' -> 1000 ml."""
    u = unit.lower().replace("+-", "").strip()
    m = re.match(r"(\d+(?:\.\d+)?)\s*x\s*(\d+)\s*g", u)
    if m:
        return UnitSpec(float(m.group(1)), "pack")
    m = re.match(r"(\d+(?:\.\d+)?)\s*(kg|g|ml|liter|l|biji)", u)
    if not m:
        return UnitSpec(1.0, "pack")
    n, b = float(m.group(1)), m.group(2)
    if b in ("liter", "l"):
        return UnitSpec(n * 1000, "ml")
    return UnitSpec(n, b)


def load_snapshot() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    items = pd.read_parquet(DATA / "items.parquet")
    premises = pd.read_parquet(DATA / "premises.parquet")
    prices = pd.read_parquet(DATA / "prices.parquet")
    prices["date"] = pd.to_datetime(prices["date"])
    meta = json.loads((DATA / "meta.json").read_text())
    return items, premises, prices, meta


def districts(premises: pd.DataFrame) -> list[str]:
    return sorted(premises["district"].dropna().unique().tolist())


def district_prices(prices: pd.DataFrame, premises: pd.DataFrame, district: str) -> pd.DataFrame:
    """Latest price per (item, premise) in a district, using only recent observations."""
    pcodes = premises.loc[premises["district"] == district, "premise_code"]
    p = prices[prices["premise_code"].isin(pcodes)]
    if p.empty:
        return p
    cutoff = p["date"].max() - pd.Timedelta(days=RECENT_DAYS)
    p = p[p["date"] >= cutoff]
    latest = (
        p.sort_values("date")
        .groupby(["item_code", "premise_code"], as_index=False)
        .last()
    )
    return latest.merge(premises[["premise_code", "premise", "premise_type", "address"]], on="premise_code")


def item_summary(latest: pd.DataFrame) -> pd.DataFrame:
    """Per item: cheapest premise + price, median price, number of premises."""
    if latest.empty:
        return pd.DataFrame(columns=["item_code", "min_price", "median_price", "n_premises",
                                     "best_premise_code", "best_premise", "best_premise_type"])
    idx = latest.groupby("item_code")["price"].idxmin()
    best = latest.loc[idx, ["item_code", "price", "premise_code", "premise", "premise_type"]].rename(
        columns={"price": "min_price", "premise_code": "best_premise_code",
                 "premise": "best_premise", "premise_type": "best_premise_type"}
    )
    agg = latest.groupby("item_code").agg(median_price=("price", "median"), n_premises=("premise_code", "nunique")).reset_index()
    return best.merge(agg, on="item_code")


def item_trends(prices: pd.DataFrame, premises: pd.DataFrame, district: str | None = None) -> pd.DataFrame:
    """Median price now vs the previous month, per item. Uses the whole state
    data when a district has too few observations."""
    p = prices
    if district is not None:
        pcodes = premises.loc[premises["district"] == district, "premise_code"]
        pd_ = p[p["premise_code"].isin(pcodes)]
        if len(pd_) > 2000:
            p = pd_
    end = p["date"].max()
    now = p[p["date"] > end - pd.Timedelta(days=TREND_NOW_DAYS)]
    base = p[(p["date"] <= end - pd.Timedelta(days=TREND_NOW_DAYS)) &
             (p["date"] > end - pd.Timedelta(days=TREND_NOW_DAYS + TREND_BASE_DAYS))]
    n = now.groupby("item_code")["price"].median().rename("now")
    b = base.groupby("item_code")["price"].median().rename("before")
    t = pd.concat([n, b], axis=1).dropna()
    t["pct_change"] = (t["now"] / t["before"] - 1) * 100
    return t.reset_index()


def daily_series(prices: pd.DataFrame, premises: pd.DataFrame, item_code: int, district: str | None = None) -> pd.DataFrame:
    p = prices[prices["item_code"] == item_code]
    if district is not None:
        pcodes = premises.loc[premises["district"] == district, "premise_code"]
        pd_ = p[p["premise_code"].isin(pcodes)]
        if len(pd_) > 50:
            p = pd_
    return p.groupby("date")["price"].median().reset_index()
