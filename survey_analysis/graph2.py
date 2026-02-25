import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import rcParams

# ========= NASTAVENÍ =========
CSV_PATH = "survey_data.csv"
OUTPUT_FILE = "prakticky_prinos_pie.png"
DPI = 300

# ========= STYL =========
rcParams["font.size"] = 14
rcParams["axes.titlesize"] = 20
rcParams["figure.figsize"] = (8, 8)

# ========= NAČTENÍ DAT =========
df = pd.read_csv(CSV_PATH)

column = "Vidíte praktický přínos takového systému ve své práci?" #Vidí zdravotníci praktický přínos systému?

order = ["Ano", "Spíše ano", "Spíše ne", "Ne"]
counts = df[column].value_counts(normalize=True).reindex(order).fillna(0)

# barvy: pozitivní modrá, negativní červená
colors = ["#2166ac", "#67a9cf", "#f4a582", "#b2182b"]

# ========= VYKRESLENÍ =========
fig, ax = plt.subplots()

wedges, texts, autotexts = ax.pie(
    counts,
    labels=order,
    autopct=lambda p: f"{p:.0f}%" if p > 0 else "",
    startangle=90,
    colors=colors,
    wedgeprops={"edgecolor": "white", "linewidth": 2}
)

ax.set_title("Vnímání praktického přínosu systému")

plt.tight_layout()
plt.savefig(OUTPUT_FILE, dpi=DPI)
plt.show()