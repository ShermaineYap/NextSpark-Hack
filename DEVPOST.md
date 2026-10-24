# Devpost submission — copy-paste kit

Deadline: **Mon 26 Oct 2026, 10:00 pm CDT = Tue 27 Oct, 11:00 am MYT.** Submit by 10 am MYT.

## Project name
**JimatMakan** — What can I cook this week for RM50?

## Tagline (one line)
A budget meal planner for Malaysian students and families, optimised on the government's real daily grocery prices.

## Project description (paste into Devpost)

### Inspiration
Grocery prices in Malaysia move week to week, and the people hit hardest — students on allowances, B40 families — plan meals by guesswork. The government already sends officers into more than 1,000 shops and collects over 2 million prices a month (KPDN PriceCatcher), but it publishes them as raw parquet files that almost nobody uses. The official app answers *"where is this item cheapest?"* Nobody answers the question people actually have on a Sunday night: **"what can I cook this week for the money I have?"**

### What it does
You tell JimatMakan your budget, how many people, how many days, what you don't eat, and the district you shop in — or just type *"RM60 for 2 people, 5 days, no beef"*. It then:

1. **Prices 29 everyday Malaysian dishes from today's data.** Every ingredient in every recipe is mapped to a PriceCatcher item code, so ayam masak kicap or asam pedas has a real cost in your district, right now.
2. **Optimises your week.** An integer linear programme picks one dish per meal to maximise vegetables and variety (different dishes, different proteins) while staying under budget — no dish more than twice.
3. **Turns it into a shopping trip.** Instead of "buy 32 items at 15 different shops", it finds the one or two shops that cover your basket cheapest, with addresses, and re-plans if the real trip breaks the budget.
4. **Warns you before you shop.** Any ingredient in your plan that has risen or fallen more than 10% vs. last month is flagged with a price chart, so you can swap a dish.

Result for a typical run: 10 meals for 2 people in Petaling for RM56, at RM2.82 per person per meal, saving RM12–15 versus paying average prices.

### How I built it
I built this with Claude (Anthropic) as the engineer, directed by me — see *Tools & AI assistance* below for the honest split. The architecture:
- **Data:** `scripts/fetch_data.py` downloads the OpenDOSM monthly parquet files and lookup tables, filters to Klang Valley (≈560k price observations, 672 shops, latest 24 Oct 2026) and commits a 1.2 MB snapshot so the app runs offline.
- **Price engine** (`jimat/pricing.py`): per shop, keep the last 14 days; per item, cheapest and median price in the district; trend = last 7 days vs. the 30 days before; a unit parser that understands "30 biji", "5 X 79g", "1 liter".
- **Recipe bank** (`jimat/recipes.py`): 29 dishes with quantities for 2, each ingredient tied to an item code.
- **Optimiser** (`jimat/planner.py`): SciPy/HiGHS MILP with count, "dish used" and "protein used" variables; solves in ~0.3 s. Store consolidation is a greedy coverage search that penalises items a shop doesn't stock.
- **UI:** Streamlit, with a tiny rule-based parser (English/Malay) for the "just tell me" box. No API keys.
- **Tests:** pytest suite covering unit conversion, recipe-to-data integrity, budget and exclusion constraints, and the parser.

### Challenges
- PriceCatcher prices items by odd units (a tray of 30 eggs, 5 × 79 g Maggi, 10 kg rice) — recipes had to be costed as fractions of a priced unit.
- The "cheapest anywhere" plan spread a basket across 15 shops; making it a realistic trip needed a second optimisation and a feedback loop back into the budget.
- PuLP 4 changed its API mid-build; I switched to SciPy's built-in MILP, which turned out simpler and dependency-free.
- Some ingredients Malaysians cook with (ikan bilis, belacan, tofu) aren't tracked at all, so a few dishes are "-style" with stand-ins.

### What I learned
How much usable public data is sitting unused; how to formulate a real product decision as an ILP; and that in a 2-minute demo, one flow that works end-to-end beats five half-features.

### What's next
Pack-size-aware costing (buy a whole tray, use it over two weeks), more states, a WhatsApp bot front-end, and user-submitted recipes.

## Built with (Devpost tags)
python, streamlit, pandas, scipy, plotly, pyarrow, opendosm, pricecatcher

## Tools, resources & AI assistance (required by the rules)
- Data: KPDN PriceCatcher via OpenDOSM, CC BY 4.0.
- Libraries: Streamlit, pandas, PyArrow, SciPy (HiGHS), Plotly, pytest.
- AI: Claude (Anthropic), used as the engineer for the whole build, directed by me. I set the brief and made product decisions; Claude researched the hackathon and dataset, proposed the idea, and generated the data pipeline, recipe mapping, optimiser, UI, tests and write-up. I reviewed and ran every part and can explain how it works.

## Links
- Repo: https://github.com/ShermaineYap/NextSpark-Hack
- Live demo: *(deploy on Streamlit Community Cloud → share.streamlit.io → New app → this repo, main file `app.py`; takes ~3 minutes)*

---

# 2-minute video script

**0:00–0:15 — Problem (camera or title card)**
"It's Sunday night. You've got RM60, two people, five days. What do you actually cook? Malaysia's government collects two million grocery prices a month — but nobody has turned that into an answer to this question. So I built JimatMakan."

**0:15–0:35 — Input (screen)**
Type in the box: *RM60 for 2 people, 5 days, no beef* → show the form fill itself. Pick district Petaling.

**0:35–1:10 — Plan (screen)**
Point at the four numbers: 10 meals, RM56 trip, RM12 saved, RM2.82 per person per meal.
Scroll the day cards: "Every one of these dishes is costed from prices KPDN officers recorded in the last two weeks — chicken at RM X at this shop, kangkung at RM Y at that one."
Open one dish's expander to show ingredient → shop → unit price.

**1:10–1:35 — Shopping trip (screen)**
"A plan is useless if it sends you to 15 shops." Click the tab: one Econsave covers 30 items, address shown. Slide "Shops I'm willing to visit" from 2 to 1 and show the cost change.

**1:35–1:50 — Price watch (screen)**
"Before you go, it tells you what's moved." Show the sawi +33% alert and the price chart.

**1:50–2:00 — Close**
"Open data, an integer programme, and 29 everyday Malaysian recipes. JimatMakan — what can I cook this week?"

Recording tips: 1440×900 window, record with OBS/Loom, speak slower than feels natural, no music louder than your voice, upload to YouTube as *Unlisted* and test the link in an incognito window.
