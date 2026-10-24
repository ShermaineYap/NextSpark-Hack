# EXPLAIN.md — how JimatMakan works, in the words you'd use to a judge

Read this once, then open the file it points to and find the line. Each
answer is 20–40 seconds spoken.

## "Where does the data come from, and is it real?"
KPDN (the Domestic Trade ministry) sends officers into ~1,000 shops and
records prices daily; DOSM publishes them monthly as parquet files under
CC BY 4.0. `scripts/fetch_data.py` downloads the two newest months plus the
item and premise lookup tables, keeps only Selangor/KL/Putrajaya shops, and
writes `data/prices.parquet` (≈560k rows, latest 24 Oct 2026). The snapshot
is committed so the app runs without internet. Re-run the script to refresh.

## "How do you get a price for one ingredient in one district?"
`jimat/pricing.py → district_prices()`: filter to the district's premises,
keep the **last 14 days**, and take each shop's most recent observation per
item. `item_summary()` then gives, per item, the **cheapest** shop and price,
the **median** price, and how many shops stock it. Cheapest drives the plan;
median is what a shopper who doesn't compare would pay — the gap is the
"Saved" number on screen.

## "Why are units a problem?"
PriceCatcher prices things in odd units: eggs per tray of 30, Maggi as
5 × 79 g, rice per 10 kg bag, soy sauce per 345 ml. `parse_unit()` turns the
unit string into (size, base-unit); `planner.fraction_of_unit()` converts a
recipe amount (4 eggs, 300 g chicken) into a fraction of the priced unit.
A tin or bottle used whole is amount-unit `pack` = 1 priced unit.

## "How are recipes priced?"
`jimat/recipes.py` holds 29 dishes with quantities for 2 people; every
ingredient is a PriceCatcher `item_code`. `planner.price_recipes()` scales
quantities to the group size and multiplies by the cheapest unit price in the
district. Staples flagged `pantry=True` (rice, oil, sauces) are costed at the
fraction used, not the whole pack. If any ingredient has no recent price in
that district the dish is marked unavailable.

## "What exactly does the optimiser optimise?"
`planner.optimise()` is an integer linear programme solved with SciPy's
`milp` (HiGHS). Variables: `n_i` = how many times dish *i* is cooked (0–2),
`y_i` = dish used at all, `z_p` = protein type *p* used. Objective: maximise
Σ (1 + veg_score_i)·n_i + 3·Σ y_i + 4·Σ z_p — so it prefers vegetable-rich
dishes, rewards distinct dishes, and rewards distinct proteins. Constraints:
Σ n_i = number of meals, Σ cost_i·n_i ≤ budget, y_i ≤ n_i ≤ 2·y_i, and z_p ≤
Σ y_i over dishes with that protein. It solves in ~0.3 s. If infeasible, it
computes the cheapest possible plan and tells the user that number.

## "The ILP gives counts — who decides which day?"
`_arrange()`: a small pass that never puts the same dish twice in one day
and alternates proteins where it can.

## "Why isn't the shopping list just 'cheapest shop per item'?"
Because that sends you to 15 shops. `consolidate_stores()` is a greedy
coverage search: score every shop by the cost of the *whole* basket using
its own prices, with items it doesn't stock costed at 1.5× the district
minimum (a detour penalty). Pick the best shop, assign what it stocks, repeat
for the leftovers up to the user's "shops I'm willing to visit". The app
tries 1..N shops and keeps the cheapest trip.

## "Your trip costs more than the plan said — how do you stay under budget?"
In `app.py`: if the realistic trip exceeds the budget, scale the optimiser's
budget down by (budget ÷ trip cost) and re-solve, up to four times. That's
why the plan and the trip both land under the number the user typed.

## "What is 'Price watch' comparing?"
`pricing.item_trends()`: district median over the **last 7 days** vs. the
median over the **30 days before that**. Anything in the plan that moved
±10% gets a card; the chart is the daily district median from `daily_series()`.

## "And the 'Just tell me' box — is that an LLM?"
No. `jimat/ask.py` is ~40 lines of regex that understands RM amounts, people
("2 people", "2 orang"), days/hari/week, meals per day, and dietary phrases
in English and Malay. No API keys, works offline, and it's deterministic.

## "What are the limitations?"
Observed prices, not live shelf prices; shops within a district can be a few
km apart; recipe quantities are approximations; ikan bilis/belacan/tofu
aren't tracked (dried prawn stands in, dishes labelled "-style"); staples are
costed by fraction used, so a first-week shop costs more in reality.

## "What did you build vs. the AI?"
Say it plainly: you set the brief and product direction and made the calls;
Claude did the research and wrote the code and docs; you reviewed, ran and
tested it, and you can explain every module (you just did).
