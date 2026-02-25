import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import rcParams
import numpy as np

# ========= NASTAVENÍ =========
# Pokud nemáš soubor, vytvoříme testovací
try:
    df = pd.read_csv("survey_data.csv")
except FileNotFoundError:
    print("CSV nenalezeno, vytvářím testovací data...")
    data = ["Ano"] * 45 + ["Spíše ano"] * 30 + ["Spíše ne"] * 15 + ["Ne"] * 10
    df = pd.DataFrame({"Vidíte praktický přínos takového systému ve své práci?": data})

CSV_PATH = "survey_data.csv"
OUTPUT_FILE = "prakticky_prinos_donut_styled.png"
DPI = 300
COLUMN_NAME = "Vidíte praktický přínos takového systému ve své práci?"

# ========= STYL (Dle vzoru Likert grafu) =========
rcParams["font.family"] = "sans-serif"
rcParams["font.size"] = 14
rcParams["axes.titlesize"] = 22
rcParams["figure.figsize"] = (10, 10) # Větší čtvercová velikost

# ========= PŘÍPRAVA DAT =========
order = ["Ano", "Spíše ano", "Spíše ne", "Ne"]
# Filtrace pouze na sloupce, které existují v datech (pro jistotu)
existing_order = [o for o in order if o in df[COLUMN_NAME].unique()]

counts = df[COLUMN_NAME].value_counts(normalize=True).reindex(existing_order).fillna(0)
total_respondents = df[COLUMN_NAME].notna().sum()

# Barvy: Tmavě modrá, Světle modrá, Světle červená, Tmavě červená
colors_map = {
    "Ano": "#2166ac",
    "Spíše ano": "#67a9cf",
    "Spíše ne": "#f4a582",
    "Ne": "#b2182b"
}
current_colors = [colors_map[cat] for cat in existing_order]

# Definice barvy textu uvnitř výseče (bílá na tmavém, černá na světlém)
text_colors_map = {
    "Ano": "white",
    "Spíše ano": "black", # nebo white, dle preference kontrastu
    "Spíše ne": "black",
    "Ne": "white"
}
current_text_colors = [text_colors_map[cat] for cat in existing_order]

# Jemné oddělení výsečí pro atraktivnější vzhled
explode = [0.02] * len(existing_order)

# ========= VYKRESLENÍ =========
fig, ax = plt.subplots()

# Vykreslení grafu - zachytíme návratové objekty pro pozdější úpravu
wedges, texts, autotexts = ax.pie(
    counts,
    labels=existing_order,
    autopct=lambda p: f"{p:.0f}%" if p > 1 else "", # Nezobrazovat procenta pod 1%
    startangle=90,
    colors=current_colors,
    explode=explode,
    pctdistance=0.80, # Posunutí procent blíže k vnějšímu okraji
    labeldistance=1.1, # Posunutí popisků kategorií dále
    wedgeprops={
        "edgecolor": "white",
        "linewidth": 3,
        "width": 0.5 # Změna na DONUT graf (šířka prstence)
    },
    textprops={'fontsize': 16, 'fontweight': 'bold'} # Základní styl pro vnější popisky
)

# --- Detailní stylování textů ---

# 1. Stylování procent uvnitř grafu (autotexts)
for i, autotext in enumerate(autotexts):
    # Nastavení barvy textu podle podkladu (bílá/černá)
    autotext.set_color(current_text_colors[i])
    autotext.set_fontsize(18) # Větší písmo pro procenta
    autotext.set_fontweight('bold')

# 2. Stylování vnějších popisků (texts)
for text in texts:
    text.set_color("#333333") # Tmavě šedá pro vnější popisky

# --- Přidání textu do středu (Donut hole) ---
# Získáme středovou kružnici a přidáme do ní text
centre_circle = plt.Circle((0,0),0.70,fc='white')
fig.gca().add_artist(centre_circle)

ax.text(0, 0.05, "Celkem\nrespondentů", ha='center', va='bottom', fontsize=14, color='gray')
ax.text(0, -0.05, f"{total_respondents}", ha='center', va='top', fontsize=28, fontweight='bold')


ax.set_title("Vnímání praktického přínosu systému", pad=20, fontweight='bold')

plt.tight_layout()
plt.savefig(OUTPUT_FILE, dpi=DPI, bbox_inches="tight")
print(f"Graf uložen do: {OUTPUT_FILE}")
plt.show()