"""Run with:  python -m pytest -q"""
from jimat import ask
from jimat.planner import fraction_of_unit, optimise, price_recipes, consolidate_stores
from jimat.pricing import district_prices, item_summary, load_snapshot, parse_unit
from jimat.recipes import RECIPES


def test_parse_unit():
    assert parse_unit("1kg").size == 1 and parse_unit("1kg").base == "kg"
    assert parse_unit("30 biji").size == 30
    assert parse_unit("345ml").base == "ml"
    assert parse_unit("1 liter").size == 1000
    assert parse_unit("5 X 79g").base == "pack" and parse_unit("5 X 79g").size == 5


def test_fraction_of_unit():
    assert abs(fraction_of_unit(4, "biji", "30 biji") - 4 / 30) < 1e-9
    assert abs(fraction_of_unit(300, "g", "1kg") - 0.3) < 1e-9
    assert fraction_of_unit(1, "pack", "425 g") == 1


def test_every_recipe_ingredient_exists_in_lookup():
    items, _, _, _ = load_snapshot()
    codes = set(items["item_code"])
    for r in RECIPES:
        for ing in r.ingredients:
            assert ing.item_code in codes, (r.name, ing.item_code)


def test_plan_respects_budget_and_slots():
    items, premises, prices, _ = load_snapshot()
    latest = district_prices(prices, premises, "Petaling")
    priced = price_recipes(item_summary(latest), items, people=2)
    plan = optimise(priced, budget=80, days=5, meals_per_day=2, exclusions=[])
    assert plan.status == "ok"
    assert len(plan.slots) == 10
    assert plan.total_cost <= 80
    names = [p.recipe.name for p in plan.slots]
    assert max(names.count(n) for n in names) <= 2
    trip, total = consolidate_stores(plan, latest, 2)
    assert set(trip["item_code"]) == {i.item_code for p in plan.slots for i in p.ingredients}


def test_exclusions_apply():
    items, premises, prices, _ = load_snapshot()
    latest = district_prices(prices, premises, "Petaling")
    priced = price_recipes(item_summary(latest), items, people=2)
    plan = optimise(priced, budget=100, days=3, meals_per_day=2, exclusions=["No beef", "No chicken"])
    assert all(p.recipe.protein not in ("beef", "chicken") for p in plan.slots)


def test_ask_parser():
    a = ask.parse("RM60 for 2 people, 5 days, no beef")
    assert (a.budget, a.people, a.days) == (60, 2, 5) and "No beef" in a.exclusions
    b = ask.parse("rm40 2 orang 3 hari vegetarian")
    assert (b.budget, b.people, b.days) == (40, 2, 3) and "Vegetarian only" in b.exclusions
