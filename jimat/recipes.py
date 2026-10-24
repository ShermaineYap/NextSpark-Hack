"""Recipe bank: everyday Malaysian home-cooked dishes, with every ingredient
mapped to a KPDN PriceCatcher item_code so the dish can be priced from
real data.

Quantities are for 2 servings. Units are base units ("kg", "g", "ml",
"biji", "pack") and are converted against the item's priced unit by the
pricing engine (e.g. eggs are priced per tray of 30, so 4 biji costs 4/30
of a tray).

`pantry=True` marks staples (oil, rice, sauces) that a kitchen usually
already has; they are costed at the fraction actually used.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Item codes (from data/items.parquet) — named here so recipes read naturally.
AYAM = 1            # AYAM BERSIH - STANDARD, 1kg
AYAM_WING = 1804
AYAM_DRUMSTICK = 1550
AYAM_THIGH = 1552
TELUR = 1110        # TELUR AYAM GRED B, 30 biji
IKAN_KEMBUNG = 1476
IKAN_SELAR = 70
IKAN_SELAYANG = 2045
IKAN_CENCARU = 47
IKAN_TONGKOL = 2047
IKAN_KELI = 88
IKAN_TILAPIA = 1921
IKAN_KERISI = 1436
UDANG = 1555        # vannamei 41-60/kg
SOTONG = 845
DAGING = 14         # DAGING KERBAU IMPORT (INDIA) TOP SIDE — the everyday "daging"
KAMBING = 9
SARDIN_TIN = 191    # SARDIN CAP AYAM 425g
IKAN_BILIS = 1562   # UDANG KERING stands in (ikan bilis isn't tracked) — see note in README
KACANG_DAL = 1422
KACANG_TANAH = 368

TOMATO = 114
TIMUN = 113
HALIA = 95
LOBAK_MERAH = 109
CILI_HIJAU = 92
CILI_MERAH = 94
CILI_API = 716
CILI_KERING = 1899
KUBIS_BUNGA = 1481
KUBIS = 104
KACANG_PANJANG = 98
KACANG_BUNCIS = 97
BENDI = 96
SAWI = 1558
KANGKUNG = 1559
BAYAM = 1556
KAILAN = 1560
TERUNG = 1923
BROKOLI = 1479
LENGKUAS = 1819
KUNYIT = 108
LOBAK_PUTIH = 2087
CAPSICUM = 1128
BAWANG_BESAR = 129
BAWANG_PUTIH = 1564
BAWANG_MERAH = 1442
KENTANG = 1131
LIMAU_NIPIS = 1132

BERAS = 2068        # 10 kg bag
MINYAK = 1094       # 1 kg bottle
KICAP = 214         # 345 ml
SOS_TIRAM = 1138    # 340 g
SOS_CILI = 1070
SOS_TOMATO = 217
SANTAN = 1611       # Kara 200 ml
BIHUN = 1584        # 400 g
MAGGI = 1976        # 5 x 79 g
TEPUNG = 917        # 1 kg
GULA = 1589
KRIMER = 883        # 500 g


@dataclass(frozen=True)
class Ingredient:
    item_code: int
    amount: float
    unit: str            # kg | g | ml | biji | pack
    pantry: bool = False


@dataclass(frozen=True)
class Recipe:
    name: str
    protein: str         # chicken | fish | seafood | egg | beef | mutton | veg
    veg_score: int       # rough "how much vegetable is on the plate" 0-3
    minutes: int
    ingredients: tuple[Ingredient, ...]
    tags: tuple[str, ...] = field(default_factory=tuple)
    note: str = ""


def I(code: int, amount: float, unit: str, pantry: bool = False) -> Ingredient:  # noqa: E743
    return Ingredient(code, amount, unit, pantry)


RICE = (I(BERAS, 0.3, "kg", True),)
OIL = (I(MINYAK, 0.03, "kg", True),)
AROMATICS = (I(BAWANG_BESAR, 0.08, "kg"), I(BAWANG_PUTIH, 0.02, "kg"))

RECIPES: tuple[Recipe, ...] = (
    # ---------- chicken ----------
    Recipe("Ayam Masak Kicap", "chicken", 1, 30,
           (I(AYAM, 0.5, "kg"), I(KICAP, 40, "ml", True), I(HALIA, 0.02, "kg"),
            I(CILI_MERAH, 0.03, "kg"), *AROMATICS, *RICE, *OIL),
           ("halal", "kid-friendly")),
    Recipe("Ayam Goreng Kunyit", "chicken", 0, 25,
           (I(AYAM, 0.5, "kg"), I(KUNYIT, 0.02, "kg"), I(TEPUNG, 30, "g", True),
            I(BAWANG_PUTIH, 0.02, "kg"), *RICE, *OIL),
           ("halal", "kid-friendly")),
    Recipe("Ayam Masak Merah", "chicken", 1, 40,
           (I(AYAM, 0.5, "kg"), I(SOS_TOMATO, 60, "ml", True), I(SOS_CILI, 40, "ml", True),
            I(TOMATO, 0.15, "kg"), I(CILI_KERING, 0.02, "kg"), *AROMATICS, *RICE, *OIL),
           ("halal",)),
    Recipe("Kari Ayam", "chicken", 2, 45,
           (I(AYAM, 0.5, "kg"), I(KENTANG, 0.25, "kg"), I(SANTAN, 200, "ml"),
            I(CILI_KERING, 0.02, "kg"), I(HALIA, 0.02, "kg"), *AROMATICS, *RICE, *OIL),
           ("halal",)),
    Recipe("Nasi Goreng Ayam", "chicken", 1, 20,
           (I(AYAM, 0.2, "kg"), I(TELUR, 2, "biji"), I(SAWI, 0.15, "kg"), I(KICAP, 20, "ml", True),
            I(CILI_API, 0.01, "kg"), *AROMATICS, *RICE, *OIL),
           ("halal", "quick", "kid-friendly")),
    Recipe("Sup Ayam dengan Sayur", "chicken", 2, 35,
           (I(AYAM_DRUMSTICK, 0.4, "kg"), I(LOBAK_MERAH, 0.15, "kg"), I(KENTANG, 0.2, "kg"),
            I(KUBIS, 0.15, "kg"), I(HALIA, 0.02, "kg"), *AROMATICS, *RICE, *OIL),
           ("halal", "kid-friendly")),
    Recipe("Kepak Ayam Bakar Madu-Kicap", "chicken", 1, 35,
           (I(AYAM_WING, 0.5, "kg"), I(KICAP, 40, "ml", True), I(GULA, 15, "g", True),
            I(TIMUN, 0.15, "kg"), I(BAWANG_PUTIH, 0.02, "kg"), *RICE, *OIL),
           ("halal", "kid-friendly")),
    Recipe("Mee Hoon Goreng Ayam", "chicken", 1, 20,
           (I(BIHUN, 160, "g"), I(AYAM, 0.15, "kg"), I(TELUR, 2, "biji"), I(SAWI, 0.15, "kg"),
            I(KICAP, 20, "ml", True), I(CILI_MERAH, 0.02, "kg"), *AROMATICS, *OIL),
           ("halal", "quick")),
    # ---------- fish ----------
    Recipe("Ikan Kembung Goreng + Sambal", "fish", 1, 25,
           (I(IKAN_KEMBUNG, 0.5, "kg"), I(KUNYIT, 0.01, "kg"), I(CILI_MERAH, 0.05, "kg"),
            I(BAWANG_MERAH, 0.05, "kg"), I(LIMAU_NIPIS, 0.03, "kg"), I(TIMUN, 0.15, "kg"), *RICE, *OIL),
           ("halal",)),
    Recipe("Ikan Selar Goreng Cili", "fish", 1, 25,
           (I(IKAN_SELAR, 0.5, "kg"), I(CILI_MERAH, 0.05, "kg"), I(KUNYIT, 0.01, "kg"),
            I(BAWANG_MERAH, 0.05, "kg"), I(TOMATO, 0.1, "kg"), *RICE, *OIL),
           ("halal",)),
    Recipe("Asam Pedas Ikan Tongkol", "fish", 2, 40,
           (I(IKAN_TONGKOL, 0.5, "kg"), I(BENDI, 0.15, "kg"), I(TOMATO, 0.15, "kg"),
            I(CILI_KERING, 0.03, "kg"), I(LENGKUAS, 0.02, "kg"), I(KUNYIT, 0.01, "kg"),
            *AROMATICS, *RICE, *OIL),
           ("halal",)),
    Recipe("Ikan Keli Masak Lemak Cili Api", "fish", 1, 35,
           (I(IKAN_KELI, 0.5, "kg"), I(SANTAN, 200, "ml"), I(CILI_API, 0.03, "kg"),
            I(KUNYIT, 0.02, "kg"), I(LENGKUAS, 0.02, "kg"), I(BAWANG_MERAH, 0.05, "kg"), *RICE, *OIL),
           ("halal",)),
    Recipe("Ikan Tilapia Stim Halia", "fish", 1, 25,
           (I(IKAN_TILAPIA, 0.6, "kg"), I(HALIA, 0.04, "kg"), I(KICAP, 30, "ml", True),
            I(CILI_MERAH, 0.02, "kg"), I(SAWI, 0.15, "kg"), *RICE, *OIL),
           ("halal", "kid-friendly")),
    Recipe("Ikan Cencaru Sumbat Sambal", "fish", 1, 35,
           (I(IKAN_CENCARU, 0.5, "kg"), I(CILI_MERAH, 0.06, "kg"), I(BAWANG_MERAH, 0.06, "kg"),
            I(LIMAU_NIPIS, 0.03, "kg"), I(TIMUN, 0.15, "kg"), *RICE, *OIL),
           ("halal",)),
    Recipe("Sardin Masak Cili + Telur Dadar", "fish", 1, 15,
           (I(SARDIN_TIN, 1, "pack"), I(TELUR, 3, "biji"), I(TOMATO, 0.1, "kg"),
            I(CILI_MERAH, 0.02, "kg"), I(LIMAU_NIPIS, 0.02, "kg"), *AROMATICS, *RICE, *OIL),
           ("halal", "quick", "budget")),
    # ---------- seafood ----------
    Recipe("Udang Masak Sambal Tumis", "seafood", 1, 25,
           (I(UDANG, 0.4, "kg"), I(CILI_MERAH, 0.06, "kg"), I(BAWANG_MERAH, 0.06, "kg"),
            I(TOMATO, 0.1, "kg"), I(KACANG_PANJANG, 0.1, "kg"), *RICE, *OIL),
           ("halal",)),
    Recipe("Sotong Goreng Kunyit", "seafood", 1, 20,
           (I(SOTONG, 0.4, "kg"), I(KUNYIT, 0.02, "kg"), I(BAWANG_BESAR, 0.1, "kg"),
            I(CILI_HIJAU, 0.03, "kg"), I(SAWI, 0.15, "kg"), *RICE, *OIL),
           ("halal", "quick")),
    # ---------- egg / vegetarian ----------
    Recipe("Telur Masak Kicap + Sayur Goreng", "egg", 2, 15,
           (I(TELUR, 4, "biji"), I(KICAP, 30, "ml", True), I(KANGKUNG, 0.25, "kg"),
            I(CILI_MERAH, 0.02, "kg"), *AROMATICS, *RICE, *OIL),
           ("halal", "quick", "budget", "vegetarian")),
    Recipe("Sayur Campur Goreng + Telur Dadar", "egg", 3, 20,
           (I(TELUR, 3, "biji"), I(KUBIS_BUNGA, 0.2, "kg"), I(LOBAK_MERAH, 0.1, "kg"),
            I(KACANG_BUNCIS, 0.1, "kg"), I(SOS_TIRAM, 20, "ml", True), *AROMATICS, *RICE, *OIL),
           ("halal", "quick", "budget")),
    Recipe("Dhal Sayur + Roti/Nasi", "veg", 2, 40,
           (I(KACANG_DAL, 0.2, "kg"), I(LOBAK_MERAH, 0.1, "kg"), I(KENTANG, 0.15, "kg"),
            I(TOMATO, 0.1, "kg"), I(KUNYIT, 0.01, "kg"), I(CILI_HIJAU, 0.02, "kg"), *AROMATICS, *RICE, *OIL),
           ("halal", "budget", "vegetarian")),
    Recipe("Kangkung Belacan-style + Telur Rebus", "egg", 2, 15,
           (I(KANGKUNG, 0.3, "kg"), I(TELUR, 4, "biji"), I(CILI_MERAH, 0.03, "kg"),
            I(IKAN_BILIS, 20, "g"), *AROMATICS, *RICE, *OIL),
           ("halal", "quick", "budget")),
    Recipe("Terung Masak Sambal + Telur", "egg", 2, 25,
           (I(TERUNG, 0.4, "kg"), I(TELUR, 3, "biji"), I(CILI_MERAH, 0.05, "kg"),
            I(BAWANG_MERAH, 0.05, "kg"), I(TOMATO, 0.1, "kg"), *RICE, *OIL),
           ("halal", "budget", "vegetarian")),
    Recipe("Kailan Ikan Masin-style + Telur Dadar", "egg", 2, 15,
           (I(KAILAN, 0.3, "kg"), I(TELUR, 3, "biji"), I(IKAN_BILIS, 20, "g"),
            I(SOS_TIRAM, 20, "ml", True), *AROMATICS, *RICE, *OIL),
           ("halal", "quick", "budget")),
    Recipe("Mee Goreng Mamak-style (Maggi)", "egg", 1, 15,
           (I(MAGGI, 0.4, "pack"), I(TELUR, 2, "biji"), I(SAWI, 0.15, "kg"), I(KENTANG, 0.1, "kg"),
            I(SOS_TOMATO, 30, "ml", True), I(SOS_CILI, 30, "ml", True), I(BAWANG_BESAR, 0.08, "kg"), *OIL),
           ("halal", "quick", "budget", "vegetarian")),
    Recipe("Bayam Sup Bening + Telur", "egg", 2, 15,
           (I(BAYAM, 0.3, "kg"), I(TELUR, 3, "biji"), I(IKAN_BILIS, 15, "g"),
            I(BAWANG_PUTIH, 0.02, "kg"), *RICE, *OIL),
           ("halal", "quick", "budget")),
    Recipe("Brokoli Goreng Bawang Putih + Telur Bistik", "egg", 3, 20,
           (I(BROKOLI, 0.3, "kg"), I(TELUR, 3, "biji"), I(BAWANG_PUTIH, 0.03, "kg"),
            I(SOS_TIRAM, 20, "ml", True), I(LOBAK_MERAH, 0.1, "kg"), *RICE, *OIL),
           ("halal", "quick")),
    # ---------- beef / mutton ----------
    Recipe("Daging Masak Kicap Berlada", "beef", 1, 45,
           (I(DAGING, 0.4, "kg"), I(KICAP, 40, "ml", True), I(CILI_MERAH, 0.05, "kg"),
            I(CAPSICUM, 0.1, "kg"), I(HALIA, 0.02, "kg"), *AROMATICS, *RICE, *OIL),
           ("halal",)),
    Recipe("Daging Masak Kurma-style dengan Kentang", "beef", 2, 60,
           (I(DAGING, 0.4, "kg"), I(KENTANG, 0.25, "kg"), I(SANTAN, 200, "ml"),
            I(HALIA, 0.02, "kg"), I(LOBAK_MERAH, 0.1, "kg"), *AROMATICS, *RICE, *OIL),
           ("halal",)),
    Recipe("Kambing Masak Kari", "mutton", 1, 60,
           (I(KAMBING, 0.4, "kg"), I(KENTANG, 0.2, "kg"), I(SANTAN, 200, "ml"),
            I(CILI_KERING, 0.03, "kg"), I(HALIA, 0.02, "kg"), *AROMATICS, *RICE, *OIL),
           ("halal",)),
)

PROTEIN_LABEL = {
    "chicken": "Ayam", "fish": "Ikan", "seafood": "Makanan laut", "egg": "Telur",
    "beef": "Daging", "mutton": "Kambing", "veg": "Sayur / kekacang",
}
