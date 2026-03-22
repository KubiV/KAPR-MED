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
rcParams["font.family"] = "Arial"
rcParams["font.size"] = 14
rcParams["axes.titlesize"] = 20
rcParams["axes.labelsize"] = 16
rcParams["figure.figsize"] = (14, 10) # Ještě o kousek vyšší pro popisky nad kraji
rcParams["axes.spines.top"] = False
rcParams["axes.spines.right"] = False
rcParams["axes.spines.left"] = False # Skrytí linky levé osy
rcParams["axes.spines.bottom"] = False # Skrytí linky osy X

# ========= NAČTENÍ DAT =========
try:
    df = pd.read_csv(CSV_PATH)
except FileNotFoundError:
    print("Soubor nenalezen, generuji testovací data...")
    np.random.seed(42)
    test_data = {
        "Jak často si musíte ve zdravotnické dokumentace „vymýšlet“ některé údaje? (Např. Časy během KPR, podané léky, vitální parametry, apod.)": np.random.randint(1, 11, 100),
        "Přesnost dokumentace": np.random.randint(1, 11, 100),
        "Úsporu času ": np.random.randint(1, 11, 100),
        "Možnost zpětné analýzy": np.random.randint(1, 11, 100),
        "Snížení zátěže personálu": np.random.randint(1, 11, 100)
    }
    
    df = pd.DataFrame(test_data)
    
    # OPRAVA: Převedeme celou tabulku na typ 'object', abychom do ní mohli vkládat texty
    df = df.astype(object) 
    
    cols = list(df.columns)
    df.loc[0, cols[0]] = "Často"
    df.loc[1, cols[0]] = "Nikdy"
    df.loc[2, cols[1]] = "Nezlepší"

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
# fig, ax = plt.subplots(tight_layout=True) # tighten_layout může pomoci, ale upravíme ručně
fig, ax = plt.subplots()
fig.patch.set_alpha(0)  # Transparentní pozadí figure
ax.patch.set_alpha(0)   # Transparentní pozadí plochy grafu (pod řádky)

categories = list(range(1, 11))
colors = [
    "#053061", "#2166ac", "#4393c3", "#92c5de", "#d1e5f0",
    "#f7f7f7", "#fddbc7", "#f4a582", "#d6604d", "#b2182b"
]

# Zvětšení mezer mezi řádky (násobeno 1.8), aby se nad pruh vešlo více textu
y_positions = np.arange(len(existing_cols)) * 1.8
display_names_plotted = [column_mapping[col] for col in existing_cols]

for i, col in enumerate(existing_cols):
    counts = df[col].value_counts(normalize=True).reindex(categories).fillna(0)
    cumulative = 0

    # Vykreslení pruhů
    for j, cat in enumerate(categories):
        value = counts.get(cat, 0) * 100 
        
        if value > 0:
            ax.barh(
                y_positions[i],
                value,
                left=cumulative,
                color=colors[j],
                edgecolor="white",
                height=0.7 # Trochu tlustší pruh
            )
            
            # Čísla uvnitř pruhů
            if value >= 4:
                text_color = "black" if 3 <= j <= 6 else "white"
                ax.text(
                    cumulative + (value / 2), 
                    y_positions[i], 
                    f"{int(round(value))}%", 
                    ha='center', va='center', 
                    color=text_color, fontsize=16, fontweight='bold'
                )
                
        cumulative += value

    # Popisky otázek a konců škály
    display_name = display_names_plotted[i]
    left_text, right_text = row_labels[display_name]
    
    # 1. Název otázky centrovaný NAD pruhem (y_pos + 0.6)
    ax.text(50, y_positions[i] + 0.6, display_name, ha='center', va='bottom', 
            fontsize=16, fontweight='bold', color='black')
    
    # ------------------------------------------------------------------
    # NOVÉ: Popisky konců škály ("Nikdy/Často") přesunuty NAD PRUH na kraje
    # ------------------------------------------------------------------
    # Nastavíme stejnou vertikální výšku jako název otázky, va='bottom'
    # Ale změníme x pozice na 0 a 100 a změníme ha (horizontální zarovnání)
    label_y_pos = y_positions[i] + 0.6
    
    # Levý popis ("Nikdy"): x=0, zarovnat doleva (ha='left')
    ax.text(0, label_y_pos, left_text, ha='left', va='bottom', 
            fontsize=16, fontweight='bold', color='#555555')
    
    # Pravý popis ("Často"): x=100, zarovnat doprava (ha='right')
    ax.text(100, label_y_pos, right_text, ha='right', va='bottom', 
            fontsize=16, fontweight='bold', color='#555555')


# Skryjeme původní osu Y
ax.set_yticks([])

# ==============================================================
# OSE X (Zachováno předchozí nastavení)
# ==============================================================
ax.set_xlim(0, 100)
ax.set_xticks(np.arange(10, 101, 10)) 
ax.set_xticklabels(['1', '2', '3', '4', '5', '6', '7', '8', '9', '10'])
ax.tick_params(axis='x', length=0) 

# Obarvení čísel na ose X
for i, label in enumerate(ax.get_xticklabels()):
    label.set_color(colors[i])
    label.set_fontweight('bold')
    outline_color = "black"
    label.set_path_effects([pe.withStroke(linewidth=1, foreground=outline_color)])

ax.set_xlabel("Škála hodnocení", labelpad=15)
ax.set_title("Očekávaný přínos AI systému", pad=40) # Ještě větší odstup titulu

# Úprava okrajů plátna - "left" jsme zmenšili, "right" zvětšili pro popisky, "top" pro název
plt.subplots_adjust(left=0.05, right=0.95, top=0.9, bottom=0.1)

plt.savefig(OUTPUT_FILE, dpi=DPI, bbox_inches="tight", transparent=True)
plt.show()