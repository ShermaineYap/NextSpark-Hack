"""Meal-plan optimiser.

Given today's prices in a district, pick one dish per meal slot so that the
week is as varied and vegetable-rich as possible while the total ingredient
cost stays under budget. Solved as a small integer linear programme with
PuLP/CBC; falls back to a greedy heuristic if the solver is unavailable.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .pricing import parse_unit
from .recipes import RECIPES, Recipe

MAX_REPEAT = 2          # a dish may appear at most twice in a plan
MISSING_PENALTY = 1.5   # store-consolidation: multiplier for items a store doesn't stock
VARIETY_BONUS = 3.0     # reward per distinct dish used
PROTEIN_BONUS = 4.0     # reward per distinct protein type used

EXCLUSION_RULES = {
    "No beef": lambda r: r.protein != "beef",
    "No mutton": lambda r: r.protein != "mutton",
    "No chicken": lambda r: r.protein != "chicken",
    "No seafood (fish, prawn, squid)": lambda r: r.protein not in ("fish", "seafood"),
    "Vegetarian only": lambda r: r.protein in ("veg", "egg") and "vegetarian" in r.tags,
    "Quick meals only (≤ 25 min)": lambda r: r.minutes <= 25,
}


@dataclass
class PricedIngredient:
    item_code: int
    item: str
    unit: str
    amount: float
    amount_unit: str
    pantry: bool
    unit_price: float | None     # price of one priced unit at the cheapest premise
    cost: float | None           # cost of the amount actually used
    premise: str | None
    premise_type: str | None
    premise_code: int | None


@dataclass
class PricedRecipe:
    recipe: Recipe
    cost: float                  # for the requested number of people, at cheapest prices
    fresh_cost: float            # excluding pantry staples
    median_cost: float           # same basket at district median prices (what a casual shopper pays)
    ingredients: list[PricedIngredient]
    missing: list[str] = field(default_factory=list)

    @property
    def available(self) -> bool:
        return not self.missing


def fraction_of_unit(amount: float, amount_unit: str, priced_unit: str) -> float:
    """How many priced units does `amount amount_unit` represent?"""
    if amount_unit == "pack":          # "pack" = one priced unit (a tin, a bottle, a bag)
        return amount
    spec = parse_unit(priced_unit)
    a, u = amount, amount_unit
    if spec.base == "kg" and u == "g":
        a, u = a / 1000, "kg"
    if spec.base == "g" and u == "kg":
        a, u = a * 1000, "g"
    if spec.base == "ml" and u == "g":      # sauces: treat 1 g ≈ 1 ml
        u = "ml"
    if spec.base == "g" and u == "ml":
        u = "g"
    if u != spec.base:
        raise ValueError(f"cannot convert {amount_unit} to {priced_unit}")
    return a / spec.size


def price_recipes(summary: pd.DataFrame, items: pd.DataFrame, people: int) -> list[PricedRecipe]:
    s = summary.set_index("item_code")
    names = items.set_index("item_code")
    scale = people / 2.0
    out = []
    for r in RECIPES:
        ings, missing, cost, fresh, med = [], [], 0.0, 0.0, 0.0
        for ing in r.ingredients:
            row = names.loc[ing.item_code]
            frac = fraction_of_unit(ing.amount * scale, ing.unit, row["unit"])
            if ing.item_code in s.index:
                p = s.loc[ing.item_code]
                c = frac * float(p["min_price"])
                cost += c
                med += frac * float(p["median_price"])
                if not ing.pantry:
                    fresh += c
                ings.append(PricedIngredient(ing.item_code, row["item"], row["unit"], ing.amount * scale,
                                             ing.unit, ing.pantry, float(p["min_price"]), c,
                                             p["best_premise"], p["best_premise_type"], int(p["best_premise_code"])))
            else:
                missing.append(row["item"])
                ings.append(PricedIngredient(ing.item_code, row["item"], row["unit"], ing.amount * scale,
                                             ing.unit, ing.pantry, None, None, None, None, None))
        out.append(PricedRecipe(r, round(cost, 2), round(fresh, 2), round(med, 2), ings, missing))
    return out


def _score(pr: PricedRecipe) -> float:
    return 1.0 + pr.recipe.veg_score


@dataclass
class Plan:
    slots: list[PricedRecipe]
    total_cost: float
    status: str
    message: str = ""


def optimise(priced: list[PricedRecipe], budget: float, days: int, meals_per_day: int,
             exclusions: list[str]) -> Plan:
    cands = [p for p in priced if p.available and all(EXCLUSION_RULES[e](p.recipe) for e in exclusions)]
    n_slots = days * meals_per_day
    if not cands:
        return Plan([], 0.0, "no_recipes", "No dishes match those filters with today's data.")
    if len(cands) * MAX_REPEAT < n_slots:
        return Plan([], 0.0, "too_few",
                    f"Only {len(cands)} dishes match those filters, and each can appear at most "
                    f"{MAX_REPEAT}× — that covers {len(cands) * MAX_REPEAT} meals, not {n_slots}. "
                    "Try fewer days or relax a filter.")

    try:
        import numpy as np
        from scipy.optimize import Bounds, LinearConstraint, milp
    except ImportError:  # pragma: no cover
        return _greedy(cands, budget, n_slots)

    # Decision variables (all binary):
    #   n[i]  = how many times dish i is cooked   (integer 0..MAX_REPEAT, modelled via count)
    #   y[i]  = 1 if dish i is used at all
    #   z[p]  = 1 if protein type p appears
    # Slot assignment is done afterwards by _arrange(); the ILP only needs counts.
    R = len(cands)
    proteins = sorted({c.recipe.protein for c in cands})
    P = len(proteins)
    nv = R + R + P                       # [n..., y..., z...]
    c = np.zeros(nv)
    c[:R] = [-_score(cd) for cd in cands]          # milp minimises → negate
    c[R:2 * R] = -VARIETY_BONUS
    c[2 * R:] = -PROTEIN_BONUS

    A, lo, hi = [], [], []
    # exactly n_slots meals
    row = np.zeros(nv); row[:R] = 1; A.append(row); lo.append(n_slots); hi.append(n_slots)
    # budget
    row = np.zeros(nv); row[:R] = [cd.cost for cd in cands]; A.append(row); lo.append(-np.inf); hi.append(budget)
    # y_i <= n_i  and  n_i <= MAX_REPEAT * y_i
    for i in range(R):
        row = np.zeros(nv); row[R + i] = 1; row[i] = -1; A.append(row); lo.append(-np.inf); hi.append(0)
        row = np.zeros(nv); row[i] = 1; row[R + i] = -MAX_REPEAT; A.append(row); lo.append(-np.inf); hi.append(0)
    # z_p <= sum y_i over dishes with protein p
    for k, p in enumerate(proteins):
        row = np.zeros(nv); row[2 * R + k] = 1
        for i in range(R):
            if cands[i].recipe.protein == p:
                row[R + i] = -1
        A.append(row); lo.append(-np.inf); hi.append(0)

    ub = np.ones(nv); ub[:R] = MAX_REPEAT
    res = milp(c, constraints=LinearConstraint(np.array(A), lo, hi),
               integrality=np.ones(nv), bounds=Bounds(np.zeros(nv), ub),
               options={"time_limit": 20})
    if not res.success:
        cheapest = sorted(cands, key=lambda cd: cd.cost)
        need, i, floor = n_slots, 0, 0.0
        while need > 0 and i < len(cheapest):
            k = min(MAX_REPEAT, need)
            floor += k * cheapest[i].cost
            need -= k
            i += 1
        return Plan([], 0.0, "infeasible",
                    f"RM{budget:.0f} isn't enough for {n_slots} meals with today's prices — "
                    f"the cheapest possible plan is about RM{floor:.0f}.")

    slots = []
    for i in range(R):
        for _ in range(int(round(res.x[i]))):
            slots.append(cands[i])
    slots = _arrange(slots, meals_per_day)
    return Plan(slots, round(sum(p.cost for p in slots), 2), "ok")


def _arrange(slots: list[PricedRecipe], meals_per_day: int) -> list[PricedRecipe]:
    """Order meals so the same dish doesn't land twice on one day and
    proteins alternate where possible."""
    remaining = list(slots)
    out: list[PricedRecipe] = []
    while remaining:
        prev = out[-1] if out else None
        day_start = (len(out) // meals_per_day) * meals_per_day
        same_day = out[day_start:]
        pick = None
        for strict in (True, False):
            for c in remaining:
                if any(o.recipe.name == c.recipe.name for o in same_day):
                    continue
                if strict and prev is not None and c.recipe.protein == prev.recipe.protein:
                    continue
                pick = c
                break
            if pick is not None:
                break
        if pick is None:
            pick = remaining[0]
        out.append(pick)
        remaining.remove(pick)
    return out


def _greedy(cands: list[PricedRecipe], budget: float, n_slots: int) -> Plan:
    chosen, spent, counts = [], 0.0, {}
    ranked = sorted(cands, key=lambda c: -_score(c) / max(c.cost, 0.5))
    while len(chosen) < n_slots:
        for c in ranked:
            if counts.get(c.recipe.name, 0) >= MAX_REPEAT or spent + c.cost > budget:
                continue
            chosen.append(c)
            spent += c.cost
            counts[c.recipe.name] = counts.get(c.recipe.name, 0) + 1
            break
        else:
            return Plan([], 0.0, "infeasible", "Budget too low for that many meals.")
    return Plan(chosen, round(spent, 2), "ok")


def shopping_list(plan: Plan) -> pd.DataFrame:
    """Aggregate ingredients across the plan, grouped by item, with the
    cheapest premise to buy each one at."""
    rows = []
    for pr in plan.slots:
        for ing in pr.ingredients:
            rows.append({
                "item_code": ing.item_code, "item": ing.item, "priced_unit": ing.unit,
                "amount": ing.amount, "amount_unit": ing.amount_unit, "pantry": ing.pantry,
                "unit_price": ing.unit_price, "cost": ing.cost,
                "premise": ing.premise, "premise_type": ing.premise_type, "premise_code": ing.premise_code,
            })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    g = df.groupby(["item_code", "item", "priced_unit", "amount_unit", "pantry", "unit_price",
                    "premise", "premise_type", "premise_code"], dropna=False, as_index=False).agg(
        amount=("amount", "sum"), cost=("cost", "sum"))
    g["cost"] = g["cost"].round(2)
    g["amount"] = g["amount"].round(3)
    return g.sort_values(["pantry", "premise", "cost"], ascending=[True, True, False])


def consolidate_stores(plan: Plan, latest: pd.DataFrame, max_stores: int = 2) -> tuple[pd.DataFrame, float]:
    """Turn the cheapest-anywhere list into a realistic trip to at most
    `max_stores` premises. Greedy: pick the premise that makes the whole
    basket cheapest (items it doesn't stock are costed at the district
    minimum, as if bought elsewhere), then repeat for the leftovers.

    Returns (shopping dataframe with a `premise` per item, total cost)."""
    base = shopping_list(plan)
    if base.empty:
        return base, 0.0
    need = base.groupby(["item_code", "item", "priced_unit", "amount_unit", "pantry"], as_index=False)["amount"].sum()
    need["units"] = [
        fraction_of_unit(a, au, pu) for a, au, pu in zip(need["amount"], need["amount_unit"], need["priced_unit"])
    ]
    price_at = latest.pivot_table(index="item_code", columns="premise_code", values="price", aggfunc="min")
    dist_min = price_at.min(axis=1)
    pinfo = latest.drop_duplicates("premise_code").set_index("premise_code")[["premise", "premise_type"]]

    remaining = need.copy()
    assigned = []
    for _ in range(max_stores):
        if remaining.empty:
            break
        codes = remaining["item_code"].values
        units = remaining["units"].values
        sub = price_at.reindex(codes)
        # an item the store doesn't stock means a detour: cost it at 1.5x the
        # district minimum so stores with better coverage win
        fallback = (dist_min.reindex(codes).values * MISSING_PENALTY)[:, None]
        filled = sub.fillna(pd.DataFrame(fallback.repeat(sub.shape[1], axis=1), index=sub.index, columns=sub.columns))
        basket = (filled.values * units[:, None]).sum(axis=0)
        best = sub.columns[int(basket.argmin())]
        here = sub[best].notna().values
        chosen = remaining[here].copy()
        chosen["premise_code"] = best
        chosen["premise"] = pinfo.loc[best, "premise"]
        chosen["premise_type"] = pinfo.loc[best, "premise_type"]
        chosen["unit_price"] = sub.loc[chosen["item_code"], best].values
        chosen["extra"] = False
        assigned.append(chosen)
        remaining = remaining[~here]
    if not remaining.empty:   # anything no chosen store stocks: cheapest anywhere
        best_codes = price_at.reindex(remaining["item_code"]).idxmin(axis=1)
        rem = remaining.copy()
        rem["premise_code"] = best_codes.values
        rem["premise"] = pinfo.loc[rem["premise_code"], "premise"].values
        rem["premise_type"] = pinfo.loc[rem["premise_code"], "premise_type"].values
        rem["unit_price"] = dist_min.reindex(rem["item_code"]).values
        rem["extra"] = True          # not stocked at any chosen stop
        assigned.append(rem)
    out = pd.concat(assigned, ignore_index=True)
    out["cost"] = (out["unit_price"] * out["units"]).round(2)
    out = out.sort_values(["extra", "premise", "pantry", "cost"], ascending=[True, True, True, False]).reset_index(drop=True)
    return out, float(out["cost"].sum().round(2))
