"""JimatMakan — "What can I cook this week for RM50?"

Budget meal planner for Malaysian students and families, powered by the
government's daily-collected grocery prices (KPDN PriceCatcher / OpenDOSM).
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from jimat import ask as askmod
from jimat.planner import (EXCLUSION_RULES, consolidate_stores, optimise,
                           price_recipes, shopping_list)
from jimat.pricing import (daily_series, district_prices, districts,
                           item_summary, item_trends, load_snapshot)
from jimat.recipes import PROTEIN_LABEL

st.set_page_config(page_title="JimatMakan", page_icon="🍛", layout="wide")

CSS = """
<style>
h1, h2, h3 { font-family: Georgia, 'Times New Roman', serif; letter-spacing: -0.01em; }
.jm-hero { font-size: 2.6rem; line-height: 1.1; margin: 0 0 .2rem 0; }
.jm-sub { color: #6b6259; font-size: 1.05rem; margin-bottom: 1rem; }
.jm-day { background: #fff; border: 1px solid #ead9c4; border-radius: 14px; padding: 14px 16px; margin-bottom: 12px; }
.jm-day h4 { margin: 0 0 8px 0; font-family: Georgia, serif; color: #C8472B; }
.jm-meal { display:flex; justify-content:space-between; gap: 8px; padding: 6px 0; border-top: 1px dashed #ead9c4; }
.jm-meal:first-of-type { border-top: none; }
.jm-meal .n { font-weight: 600; }
.jm-meal .p { color:#6b6259; font-size:.85rem; }
.jm-meal .c { white-space:nowrap; font-variant-numeric: tabular-nums; }
.jm-pill { display:inline-block; background:#F3EBDD; border-radius: 999px; padding: 2px 10px; font-size:.78rem; margin-right:6px; color:#5a4f45; }
.jm-store { background:#fff; border-left: 5px solid #1F7A6D; border-radius: 10px; padding: 12px 16px; margin-bottom: 10px; }
.jm-store h4 { margin:0 0 4px 0; }
.jm-store .addr { color:#6b6259; font-size:.85rem; }
.jm-alert { background:#FFF1EC; border:1px solid #F3C3B7; border-radius: 10px; padding: 10px 14px; margin-bottom: 8px; }
.jm-good { background:#ECF7F4; border:1px solid #BFE3DA; border-radius: 10px; padding: 10px 14px; margin-bottom: 8px; }
.small { color:#6b6259; font-size:.85rem; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def _load():
    return load_snapshot()


@st.cache_data(show_spinner=False)
def _district(district: str):
    items, premises, prices, _ = _load()
    latest = district_prices(prices, premises, district)
    return latest, item_summary(latest)


@st.cache_data(show_spinner=False)
def _trends(district: str):
    items, premises, prices, _ = _load()
    return item_trends(prices, premises, district).merge(items, on="item_code")


items, premises, prices, meta = _load()
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MEAL_NAMES = {1: ["Dinner"], 2: ["Lunch", "Dinner"], 3: ["Breakfast", "Lunch", "Dinner"]}

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("### 🍛 JimatMakan")
    st.caption("Plan a week of real Malaysian meals that fit your budget — priced from today's government price data.")

    quick = st.text_input("Just tell me", placeholder="RM60 for 2 people, 5 days, no beef",
                          help="Plain words are fine — English or Malay. The form below fills itself.")
    parsed = askmod.parse(quick) if quick else askmod.Ask()

    all_d = districts(premises)
    default_d = all_d.index("Petaling") if "Petaling" in all_d else 0
    district = st.selectbox("Where do you shop?", all_d, index=default_d)
    budget = st.number_input("Budget (RM)", 10.0, 1000.0, float(parsed.budget or 60.0), 5.0)
    people = st.number_input("People", 1, 8, int(parsed.people or 2))
    days = st.slider("Days", 1, 7, int(parsed.days or 5))
    meals_per_day = st.radio("Meals per day", [1, 2, 3], index=[1, 2, 3].index(parsed.meals_per_day or 2),
                             horizontal=True, format_func=lambda n: {1: "Dinner only", 2: "Lunch + dinner", 3: "All three"}[n])
    exclusions = st.multiselect("Dietary limits", list(EXCLUSION_RULES), default=parsed.exclusions)
    max_stores = st.select_slider("Shops I'm willing to visit", [1, 2, 3], value=2)
    st.caption(f"Prices: KPDN PriceCatcher via OpenDOSM · latest {meta['latest_date']} · {meta['rows']:,} observations across Klang Valley")

# ---------------------------------------------------------------- compute
latest, summary = _district(district)
if latest.empty:
    st.error("No recent price observations for that district. Try another one.")
    st.stop()
priced = price_recipes(summary, items, int(people))
plan = optimise(priced, float(budget), int(days), int(meals_per_day), exclusions)

st.markdown('<div class="jm-hero">What can I cook this week?</div>', unsafe_allow_html=True)
st.markdown(f'<div class="jm-sub">Real dishes, real prices — {latest["premise_code"].nunique()} shops in '
            f'<b>{district}</b>, {summary.shape[0]} items priced as of {meta["latest_date"]}.</div>', unsafe_allow_html=True)

if plan.status != "ok":
    st.warning(plan.message)
    st.markdown("**Cheapest dishes right now** (per plate for your group):")
    cheap = sorted([p for p in priced if p.available], key=lambda p: p.cost)[:8]
    st.dataframe(pd.DataFrame([{"Dish": p.recipe.name, "Protein": PROTEIN_LABEL[p.recipe.protein],
                                "Cost (RM)": p.cost} for p in cheap]), hide_index=True, use_container_width=True)
    st.stop()

# store trip: try 1..max_stores and keep the cheapest realistic trip.
# A real trip costs more than "cheapest anywhere", so if it blows the budget
# we tighten the optimiser's budget and re-solve until the trip fits.
def _best_trip(pl):
    bt, btot = None, float("inf")
    for k in range(1, int(max_stores) + 1):
        trip, total = consolidate_stores(pl, latest, k)
        if total < btot:
            bt, btot = trip, total
    return bt, btot

best_trip, best_total = _best_trip(plan)
inner = float(budget)
for _ in range(4):
    if best_total <= float(budget) + 0.005:
        break
    inner *= float(budget) / best_total
    replan = optimise(priced, inner, int(days), int(meals_per_day), exclusions)
    if replan.status != "ok":
        break
    plan = replan
    best_trip, best_total = _best_trip(plan)
if best_total > float(budget) + 0.005:
    st.warning(f"Closest realistic trip is RM{best_total:.2f}, a little over RM{budget:.0f}. "
               "Add a shop, a day less, or nudge the budget.")
median_total = round(sum(p.median_cost for p in plan.slots), 2)
n_meals = len(plan.slots)

# ---------------------------------------------------------------- headline
c1, c2, c3, c4 = st.columns(4)
c1.metric("Meals planned", f"{n_meals}", f"{days} days × {people} people")
c2.metric("Your trip costs", f"RM{best_total:.2f}", f"budget RM{budget:.0f}", delta_color="off")
c3.metric("Saved vs. average prices", f"RM{max(median_total - best_total, 0):.2f}",
          "by shopping where it's cheapest", delta_color="off")
c4.metric("Per meal per person", f"RM{best_total / n_meals / people:.2f}")

tab_plan, tab_shop, tab_watch, tab_how = st.tabs(["🗓️ Weekly plan", "🛒 Shopping trip", "📈 Price watch", "ℹ️ How it works"])

# ---------------------------------------------------------------- plan tab
with tab_plan:
    proteins = {}
    for p in plan.slots:
        proteins[p.recipe.protein] = proteins.get(p.recipe.protein, 0) + 1
    st.markdown("".join(f'<span class="jm-pill">{PROTEIN_LABEL[k]} × {v}</span>' for k, v in proteins.items()),
                unsafe_allow_html=True)
    st.write("")
    cols = st.columns(min(int(days), 4))
    mpd = int(meals_per_day)
    for d in range(int(days)):
        meals = plan.slots[d * mpd:(d + 1) * mpd]
        html = f'<div class="jm-day"><h4>{DAY_NAMES[d % 7]}</h4>'
        for m, pr in zip(MEAL_NAMES[mpd], meals):
            html += (f'<div class="jm-meal"><div><div class="n">{pr.recipe.name}</div>'
                     f'<div class="p">{m} · {pr.recipe.minutes} min · {PROTEIN_LABEL[pr.recipe.protein]}</div></div>'
                     f'<div class="c">RM{pr.cost:.2f}</div></div>')
        html += "</div>"
        cols[d % len(cols)].markdown(html, unsafe_allow_html=True)

    with st.expander("See what goes into each dish"):
        for pr in sorted({p.recipe.name: p for p in plan.slots}.values(), key=lambda p: p.recipe.name):
            st.markdown(f"**{pr.recipe.name}** — RM{pr.cost:.2f} for {people}")
            df = pd.DataFrame([{"Ingredient": i.item, "Amount": f"{i.amount:g} {i.amount_unit}",
                                "Cheapest at": i.premise, "Unit price": f"RM{i.unit_price:.2f} / {i.unit}",
                                "Cost": round(i.cost, 2), "Pantry": "✓" if i.pantry else ""} for i in pr.ingredients])
            st.dataframe(df, hide_index=True, use_container_width=True)

# ---------------------------------------------------------------- shop tab
with tab_shop:
    stores = best_trip["premise"].unique().tolist()
    st.markdown(f"**{len(stores)} stop{'s' if len(stores) > 1 else ''}** for the whole week. "
                f"Cheapest-anywhere total would be RM{plan.total_cost:.2f} across "
                f"{shopping_list(plan)['premise'].nunique()} shops — this trip costs RM{best_total:.2f}.")
    pinfo = premises.set_index("premise_code")
    for s in stores:
        part = best_trip[best_trip["premise"] == s]
        code = int(part["premise_code"].iloc[0])
        addr = pinfo.loc[code, "address"] if code in pinfo.index else ""
        ptype = part["premise_type"].iloc[0]
        st.markdown(f'<div class="jm-store"><h4>{s} <span class="jm-pill">{ptype}</span></h4>'
                    f'<div class="addr">{addr}</div><div><b>RM{part["cost"].sum():.2f}</b> · {len(part)} items</div></div>',
                    unsafe_allow_html=True)
        show = part[["item", "amount", "amount_unit", "unit_price", "priced_unit", "cost", "pantry"]].copy()
        show["Amount"] = show["amount"].map(lambda v: f"{v:g}") + " " + show["amount_unit"]
        show["Price"] = "RM" + show["unit_price"].map(lambda v: f"{v:.2f}") + " / " + show["priced_unit"]
        show["Pantry"] = show["pantry"].map(lambda b: "✓" if b else "")
        st.dataframe(show.rename(columns={"item": "Item", "cost": "Cost (RM)"})[["Item", "Amount", "Price", "Cost (RM)", "Pantry"]],
                     hide_index=True, use_container_width=True)
    st.markdown('<div class="small">Pantry ✓ = staples (rice, oil, sauces) costed only for the amount used — '
                'you probably already have them. Fresh items are costed at the amount the recipes need.</div>',
                unsafe_allow_html=True)

# ---------------------------------------------------------------- watch tab
with tab_watch:
    tr = _trends(district)
    used = {i.item_code for p in plan.slots for i in p.ingredients}
    mine = tr[tr["item_code"].isin(used)].sort_values("pct_change", ascending=False)
    rising = mine[mine["pct_change"] >= 10]
    falling = mine[mine["pct_change"] <= -10]
    st.markdown("**Items in your plan, this week vs. last month** (district median price)")
    if rising.empty and falling.empty:
        st.markdown('<div class="jm-good">Nothing in your basket has moved more than 10% — good week to shop.</div>',
                    unsafe_allow_html=True)
    for _, r in rising.iterrows():
        st.markdown(f'<div class="jm-alert">⚠️ <b>{r["item"].title()}</b> is up <b>{r["pct_change"]:.0f}%</b> '
                    f'(RM{r["before"]:.2f} → RM{r["now"]:.2f} per {r["unit"]}). Consider swapping a dish that uses it.</div>',
                    unsafe_allow_html=True)
    for _, r in falling.iterrows():
        st.markdown(f'<div class="jm-good">✅ <b>{r["item"].title()}</b> is down <b>{abs(r["pct_change"]):.0f}%</b> '
                    f'(RM{r["before"]:.2f} → RM{r["now"]:.2f} per {r["unit"]}). Good time to buy.</div>',
                    unsafe_allow_html=True)

    st.write("")
    pick = st.selectbox("Price history", mine["item"].tolist() if not mine.empty else tr["item"].tolist(),
                        index=0)
    code = int(tr.loc[tr["item"] == pick, "item_code"].iloc[0])
    ser = daily_series(prices, premises, code, district)
    fig = go.Figure(go.Scatter(x=ser["date"], y=ser["price"], mode="lines+markers",
                               line=dict(color="#C8472B", width=2), marker=dict(size=5)))
    fig.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", yaxis_title="RM (median)", xaxis_title=None)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#eee")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Biggest movers in fresh food across the district**")
    fresh = tr[tr["item_group"].isin(["BARANGAN SEGAR", "BARANGAN KERING"])]
    movers = pd.concat([fresh.nlargest(5, "pct_change"), fresh.nsmallest(5, "pct_change")])
    st.dataframe(movers[["item", "unit", "before", "now", "pct_change"]].rename(
        columns={"item": "Item", "unit": "Unit", "before": "Last month (RM)", "now": "This week (RM)", "pct_change": "Change %"})
        .round(2), hide_index=True, use_container_width=True)

# ---------------------------------------------------------------- how tab
with tab_how:
    st.markdown(f"""
**The problem.** Grocery prices in Malaysia move week to week, and the people hit hardest — students, B40
families — plan meals by guesswork. The government already collects **over 2 million prices a month** from
real shops (KPDN PriceCatcher), but it's published as raw parquet files that almost nobody uses.

**What JimatMakan does.** It starts from the *meal*, not the price tag:

1. **Price engine** — loads the latest PriceCatcher snapshot ({meta['rows']:,} observations, {meta['months'][0]} → {meta['latest_date']}),
   keeps the last 14 days per shop, and finds the cheapest and median price for every ingredient in **{district}**.
2. **Recipe bank** — {len(priced)} everyday Malaysian dishes, every ingredient hand-mapped to a PriceCatcher item code
   with realistic quantities, so each dish has a true cost today.
3. **Optimiser** — an integer linear programme (SciPy / HiGHS) picks {n_meals} meals that maximise
   vegetable content and variety (distinct dishes, distinct proteins) subject to your budget, with no dish more than twice.
4. **Shopping trip** — a greedy coverage search turns the cheapest-anywhere list into a trip to {max_stores} shop(s) or fewer.
5. **Price watch** — flags any ingredient in your plan that has moved ±10% vs. last month, so you can swap before you shop.

**Honest limits.** Prices are the latest *observed* by KPDN officers, not live shelf prices; the recipe
quantities are approximations; ikan bilis isn't tracked so dried prawn stands in; staples are costed by the fraction used.

Data: [KPDN PriceCatcher via OpenDOSM](https://open.dosm.gov.my/data-catalogue/pricecatcher) (CC BY 4.0).
    """)
