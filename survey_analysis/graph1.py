import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams

# ========= NASTAVENÍ =========
CSV_PATH = "survey_data.csv"   # uprav cestu
OUTPUT_FILE = "likert_graf.png"
DPI = 300

# ========= STYL PRO POSTER =========
rcParams["font.size"] = 14
rcParams["axes.titlesize"] = 20
rcParams["axes.labelsize"] = 16
rcParams["figure.figsize"] = (12, 8) # Zvětšeno na výšku pro legendu dole
rcParams["axes.spines.top"] = False
rcParams["axes.spines.right"] = False

# ========= NAČTENÍ DAT =========
# Pokud by CSV chybělo, skript spadne. Ujisti se, že CSV_PATH je správně.
df = pd.read_csv(CSV_PATH)

# Slovník mapující názvy v CSV na kratší názvy pro zobrazení v grafu
# Klíč = název v CSV, Hodnota = název v grafu na ose Y
column_mapping = {
    "Jak často si musíte ve zdravotnické dokumentace „vymýšlet“ některé údaje? (Např. Časy během KPR, podané léky, vitální parametry, apod.)": "Nutnost „vymýšlet“ údaje",
    "Přesnost dokumentace": "Zvýšení přesnosti záznamu",
    "Úsporu času ": "Úspora času při dokumentaci",
    "Možnost zpětné analýzy": "Možnost zpětné analýzy",
    "Snížení zátěže personálu": "Snížení zátěže týmu"
}

# Extrakce sloupců pro analýzu a názvů pro vykreslení
csv_columns = list(column_mapping.keys())
display_names = list(column_mapping.values())

# ========= ČIŠTĚNÍ =========
def convert_likert(x):
    if isinstance(x, str):
        x = x.strip()
        if x.lower() == "nezlepší":
            return 10  # Dle tvého popisu: mohla výrazně zlepšit=1 ... nezlepší=10
        if x.lower() == "nikdy":
            return 1
        if x.lower() == "často":
            return 10
    try:
        return int(x)
    except:
        return np.nan

# Aplikace čištění pouze na sloupce, které v CSV reálně existují
existing_cols = [col for col in csv_columns if col in df.columns]
for col in existing_cols:
    df[col] = df[col].apply(convert_likert)

# ========= VYKRESLENÍ =========
fig, ax = plt.subplots()

# Pokud je tvá škála 1-10, upravíme categories. (V původním kódu bylo 0-10).
# Pokud v datech existuje i 0, změň zpět na range(0, 11).
categories = list(range(1, 11))

# Barevná škála (10 barev pro škálu 1-10)
colors = [
    "#b2182b", "#d6604d", "#f4a582", "#fddbc7", "#f7f7f7", 
    "#d1e5f0", "#92c5de", "#4393c3", "#2166ac", "#053061"
]

# Procházíme existující sloupce v pořadí, v jakém chceme (odspodu nahoru)
y_positions = np.arange(len(existing_cols))
display_names_plotted = [column_mapping[col] for col in existing_cols]

for i, col in enumerate(existing_cols):
    counts = df[col].value_counts(normalize=True).reindex(categories).fillna(0)
    cumulative = 0

    for j, cat in enumerate(categories):
        value = counts[cat] * 100 # Převod na procenta
        
        if value > 0:
            # Vykreslení pruhu
            ax.barh(
                y_positions[i],
                value,
                left=cumulative,
                color=colors[j],
                edgecolor="white",
                height=0.65
            )
            
            # Vykreslení procent do středu pruhu (pouze pokud je pruh dost široký, např. >= 4 %)
            if value >= 4:
                # Volba barvy textu pro kontrast (tmavé okraje škály = bílý text, světlý střed = černý text)
                text_color = "black" if 3 <= j <= 6 else "white"
                
                ax.text(
                    cumulative + (value / 2), 
                    y_positions[i], 
                    f"{int(round(value))}%", 
                    ha='center', 
                    va='center', 
                    color=text_color, 
                    fontsize=12,
                    fontweight='bold'
                )
                
        cumulative += value

ax.set_yticks(y_positions)
ax.set_yticklabels(display_names_plotted)
ax.set_xlabel("Podíl respondentů (%)")
ax.set_title("Očekávaný přínos AI systému")
ax.set_xlim(0, 100)

# ========= VYSVĚTLIVKY (LEGENDA) =========
# Přidání textu pod graf pro vysvětlení smyslu škály 1-10
legend_text = (
    "Vysvětlivky škály (1 až 10):\n"
    "• Přínos pro dokumentaci: 1 (Mohla výrazně zlepšit) ➔ 10 (Nezlepší)\n"
    "• Nutnost „vymýšlet“ údaje: 1 (Nikdy) ➔ 10 (Často)"
)
fig.text(
    0.5, 0.02, legend_text, 
    ha="center", va="bottom", fontsize=12, 
    bbox=dict(facecolor='white', alpha=0.9, edgecolor='#cccccc', boxstyle='round,pad=0.5')
)

# Úprava okrajů, aby se vysvětlivky dole vešly
plt.tight_layout(rect=[0, 0.1, 1, 1]) 
plt.savefig(OUTPUT_FILE, dpi=DPI)
plt.show()