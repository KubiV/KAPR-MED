import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib import rcParams

# ========= NASTAVENÍ =========
CSV_PATH = "survey_data.csv"   # uprav cestu
OUTPUT_FILE = "likert_graf.png"
DPI = 300

# ========= STYL PRO POSTER =========
rcParams["font.family"] = "sans-serif"
rcParams["font.size"] = 14
rcParams["axes.titlesize"] = 20
rcParams["axes.labelsize"] = 16
rcParams["figure.figsize"] = (14, 9) # Trochu vyšší pro větší rozestupy
rcParams["axes.spines.top"] = False
rcParams["axes.spines.right"] = False
rcParams["axes.spines.left"] = False # Skrytí linky levé osy, když u ní nejsou popisky

# ========= NAČTENÍ DAT =========
try:
    df = pd.read_csv(CSV_PATH)
except FileNotFoundError:
    print("Soubor nenalezen, generuji testovací data...")
    df = pd.DataFrame({
        "Jak často si musíte ve zdravotnické dokumentace „vymýšlet“ některé údaje? (Např. Časy během KPR, podané léky, vitální parametry, apod.)": np.random.randint(1, 11, 100),
        "Přesnost dokumentace": np.random.randint(1, 11, 100),
        "Úsporu času ": np.random.randint(1, 11, 100),
        "Možnost zpětné analýzy": np.random.randint(1, 11, 100),
        "Snížení zátěže personálu": np.random.randint(1, 11, 100)
    })

# Slovník mapující názvy
column_mapping = {
    "Jak často si musíte ve zdravotnické dokumentace „vymýšlet“ některé údaje? (Např. Časy během KPR, podané léky, vitální parametry, apod.)": "Nutnost „vymýšlet“ údaje",
    "Přesnost dokumentace": "Zvýšení přesnosti záznamu",
    "Úsporu času ": "Úspora času při dokumentaci",
    "Možnost zpětné analýzy": "Možnost zpětné analýzy",
    "Snížení zátěže personálu": "Snížení zátěže týmu"
}

row_labels = {
    "Nutnost „vymýšlet“ údaje": ("Nikdy", "Často"),
    "Zvýšení přesnosti záznamu": ("Zlepší", "Nezlepší"),
    "Úspora času při dokumentaci": ("Zlepší", "Nezlepší"),
    "Možnost zpětné analýzy": ("Zlepší", "Nezlepší"),
    "Snížení zátěže týmu": ("Zlepší", "Nezlepší")
}

csv_columns = list(column_mapping.keys())

# ========= ČIŠTĚNÍ =========
def convert_likert(x):
    if isinstance(x, str):
        x = x.strip()
        if x.lower() == "nezlepší": return 10
        if x.lower() == "nikdy": return 1
        if x.lower() == "často": return 10
    try:
        return int(x)
    except:
        return np.nan

existing_cols = [col for col in csv_columns if col in df.columns]
for col in existing_cols:
    df[col] = df[col].apply(convert_likert)

# ========= VYKRESLENÍ =========
fig, ax = plt.subplots()

categories = list(range(1, 11))
colors = [
    "#053061", "#2166ac", "#4393c3", "#92c5de", "#d1e5f0",
    "#f7f7f7", "#fddbc7", "#f4a582", "#d6604d", "#b2182b"
]

# Zvětšení mezer mezi řádky (násobeno 1.5), aby se nad pruh vešel text
y_positions = np.arange(len(existing_cols)) * 1.5
display_names_plotted = [column_mapping[col] for col in existing_cols]

for i, col in enumerate(existing_cols):
    counts = df[col].value_counts(normalize=True).reindex(categories).fillna(0)
    cumulative = 0

    for j, cat in enumerate(categories):
        value = counts.get(cat, 0) * 100 
        
        if value > 0:
            ax.barh(
                y_positions[i],
                value,
                left=cumulative,
                color=colors[j],
                edgecolor="white",
                height=0.65
            )
            
            if value >= 4:
                text_color = "black" if 3 <= j <= 6 else "white"
                ax.text(
                    cumulative + (value / 2), 
                    y_positions[i], 
                    f"{int(round(value))}%", 
                    ha='center', va='center', 
                    color=text_color, fontsize=11, fontweight='bold'
                )
                
        cumulative += value

    display_name = display_names_plotted[i]
    left_text, right_text = row_labels[display_name]
    
    # ---------------------------------------------------------
    # NOVÉ: Název otázky centrovaný NAD pruhem (x=50, y=pozice+0.45)
    # ---------------------------------------------------------
    ax.text(50, y_positions[i] + 0.45, display_name, ha='center', va='bottom', 
            fontsize=14, fontweight='bold', color='black')
    
    # Texty vlevo a vpravo
    ax.text(-2, y_positions[i], left_text, ha='right', va='center', 
            fontsize=12, fontweight='bold', color='#444444')
    ax.text(102, y_positions[i], right_text, ha='left', va='center', 
            fontsize=12, fontweight='bold', color='#444444')


# Skryjeme původní osu Y (názvy jsme přesunuli nad pruhy)
ax.set_yticks([])

# ==============================================================
# VYLEPŠENÁ OSA X (Skrytí 0, zarovnání, barvy a dynamické obrysy)
# ==============================================================
ax.set_xlim(0, 100)

# Osa začne od 10 do 100 (krok 10), tím se zbavíme nuly
ax.set_xticks(np.arange(10, 101, 10)) 
ax.set_xticklabels(['1', '2', '3', '4', '5', '6', '7', '8', '9', '10'])

# Skryje samotné "čárky" na ose X, nechá pouze zarovnaný text
ax.tick_params(axis='x', length=0) 

# Projdeme popisky a obarvíme je + přidáme dynamický outline
for i, label in enumerate(ax.get_xticklabels()):
    # Index 'i' jde 0 až 9, odpovídá číslům 1-10 a barvám v poli 'colors'
    label.set_color(colors[i])
    label.set_fontweight('bold')
    
    # Podmínka pro barvu outline - stejná logika jako máte pro čísla v grafu
    # Indexy 3 až 6 (odpovídá číslům 4, 5, 6, 7 na škále) dostanou černý outline, zbytek bílý
    #outline_color = "black" if 4 <= i <= 8 else "white"
    outline_color = "black"
    
    label.set_path_effects([pe.withStroke(linewidth=1, foreground=outline_color)])

ax.set_xlabel("Škála hodnocení", labelpad=15)
ax.set_title("Očekávaný přínos AI systému", pad=30)

# ==============================================================
# NOVÉ: Obarvení čísel 1 až 10 na ose X dle barev z grafu
# ==============================================================
for i, label in enumerate(ax.get_xticklabels()):
    # Index 0 je prázdný řetězec (''), čísla 1-10 jsou na indexech 1 až 10
    if i > 0 and i <= len(colors):
        label.set_color(colors[i - 1])
        label.set_fontweight('bold') # Přidáme tučné písmo pro lepší čitelnost

ax.set_xlabel("Škála hodnocení", labelpad=10)
ax.set_title("Očekávaný přínos AI systému", pad=30) # Větší odstup nadpisu

# Úprava okrajů plátna - "left" jsme zmenšili, už nepotřebujeme tolik místa na původní dlouhé názvy
plt.subplots_adjust(left=0.15, right=0.85, top=0.9, bottom=0.1)

plt.savefig(OUTPUT_FILE, dpi=DPI, bbox_inches="tight")
plt.show()