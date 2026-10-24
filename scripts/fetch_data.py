"""Download the latest KPDN PriceCatcher data from OpenDOSM and build the
compact snapshot that the app reads.

Source: https://open.dosm.gov.my/data-catalogue/pricecatcher  (CC BY 4.0)

Usage:
    python scripts/fetch_data.py                 # last 2 months, Klang Valley
    python scripts/fetch_data.py --months 3 --states Selangor "W.P. Kuala Lumpur" Johor

Outputs (all parquet, small enough to commit):
    data/items.parquet     item_code, item, unit, item_group, item_category
    data/premises.parquet  premise_code, premise, address, premise_type, state, district
    data/prices.parquet    date, premise_code, item_code, price  (filtered to chosen states)
    data/meta.json         when the snapshot was built and which months it covers
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

BASE = "https://storage.data.gov.my/pricecatcher/"
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DEFAULT_STATES = ["Selangor", "W.P. Kuala Lumpur", "W.P. Putrajaya"]


def download(name: str) -> pd.DataFrame | None:
    url = f"{BASE}{name}.parquet"
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            buf = r.read()
    except Exception as e:  # noqa: BLE001
        print(f"  skip {name}: {e}", file=sys.stderr)
        return None
    df = pd.read_parquet(io.BytesIO(buf))
    print(f"  {name}: {len(df):,} rows")
    return df


def month_strings(n: int) -> list[str]:
    today = date.today()
    out = []
    y, m = today.year, today.month
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", type=int, default=2, help="how many recent months to pull")
    ap.add_argument("--states", nargs="+", default=DEFAULT_STATES)
    args = ap.parse_args()

    DATA.mkdir(exist_ok=True)
    print("Downloading lookups...")
    items = download("lookup_item")
    premises = download("lookup_premise")
    if items is None or premises is None:
        sys.exit("lookup tables unavailable")

    keep = premises[premises["state"].isin(args.states)]
    print(f"Keeping {len(keep):,} premises in {args.states}")

    frames, months = [], []
    print("Downloading monthly price files...")
    for ms in month_strings(args.months + 1):  # +1 so a brand-new month still yields history
        df = download(f"pricecatcher_{ms}")
        if df is None:
            continue
        df = df[df["premise_code"].isin(keep["premise_code"])]
        frames.append(df)
        months.append(ms)
        if len(frames) >= args.months:
            break
    if not frames:
        sys.exit("no price data downloaded")

    prices = pd.concat(frames, ignore_index=True)
    prices["date"] = pd.to_datetime(prices["date"])
    prices = prices[prices["price"] > 0]
    prices = prices.drop_duplicates(["date", "premise_code", "item_code"], keep="last")

    items.to_parquet(DATA / "items.parquet", index=False)
    keep.to_parquet(DATA / "premises.parquet", index=False)
    prices.to_parquet(DATA / "prices.parquet", index=False)
    meta = {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "months": sorted(months),
        "states": args.states,
        "rows": int(len(prices)),
        "latest_date": prices["date"].max().strftime("%Y-%m-%d"),
        "source": "KPDN PriceCatcher via OpenDOSM (CC BY 4.0)",
    }
    (DATA / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"Done: {len(prices):,} price rows, latest {meta['latest_date']}")


if __name__ == "__main__":
    main()
