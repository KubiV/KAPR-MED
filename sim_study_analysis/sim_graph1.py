import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
import matplotlib.patches as mpatches
import matplotlib.lines as mlines

# ========= NAČTENÍ A PŘÍPRAVA DAT =========
# Načtení z reálného CSV
df = pd.read_csv('sim study_analyzed.csv', sep=';')
df_valid = df.dropna(subset=['Vyhodnocení správně - ANO/NE'])

labels = []
success_rates = []
type1_rates = []
other_rates = []

# Iterace přes jednotlivé sessions a výpočet reálných procent
for s in sorted(df_valid['Session'].unique()):
    sub = df_valid[df_valid['Session'] == s]
    total = len(sub)
    ano = (sub['Vyhodnocení správně - ANO/NE'] == 'ANO').sum()
    typ1 = (sub.iloc[:, 5] == 1.0).sum()
    
    # Výpočet procent
    s_rate = ano / total * 100
    t1_rate = typ1 / total * 100
    # OPRAVA: Výpočet zbytku do přesných 100 %
    o_rate = 100.0 - s_rate - t1_rate
    
    success_rates.append(s_rate)
    type1_rates.append(t1_rate)
    other_rates.append(o_rate)
    
    label_base = f'Skupina {s}'
    if s in [1, 2]:
        labels.append(f'{label_base}\n(Subj. horší\n komunikace)')
    else:
        labels.append(f'{label_base}\n(Subj. lepší\n komunikace)')

# Výpočet pro sloupec "CELKOVĚ"
total_all = len(df_valid)
ano_all = (df_valid['Vyhodnocení správně - ANO/NE'] == 'ANO').sum()
typ1_all = (df_valid.iloc[:, 5] == 1.0).sum()

overall_rate = ano_all / total_all * 100
overall_type1 = typ1_all / total_all * 100
# OPRAVA: Výpočet zbytku pro celkový součet
overall_other = 100.0 - overall_rate - overall_type1

success_rates.append(overall_rate)
type1_rates.append(overall_type1)
other_rates.append(overall_other)
labels.append('CELKOVĚ')

# ========= NASTAVENÍ STYLU =========
rcParams["font.family"] = "Arial"
rcParams["font.size"] = 14
rcParams["axes.titlesize"] = 20
rcParams["axes.labelsize"] = 16
rcParams["figure.figsize"] = (13, 8)
rcParams["axes.spines.top"] = False
rcParams["axes.spines.right"] = False
rcParams["axes.spines.left"] = False
rcParams["axes.spines.bottom"] = False

# ========= GRAF =========
fig, ax = plt.subplots()

color_success = '#4CAF50' # Zelená
color_type1 = '#FFCA28'   # Žlutá
color_type2 = '#EF5350'   # Červená

width = 0.6
x_pos = np.arange(len(labels))

# Stacked bars
bars_success = ax.bar(x_pos, success_rates, color=color_success, width=width, edgecolor='white', linewidth=1.2)
bars_type1 = ax.bar(x_pos, type1_rates, bottom=success_rates, color=color_type1, width=width, edgecolor='white', linewidth=1.2)
bars_type2 = ax.bar(x_pos, other_rates, bottom=np.array(success_rates) + np.array(type1_rates), color=color_type2, width=width, edgecolor='white', linewidth=1.2)

# Funkce pro popisky uvnitř sloupců
def add_labels_inside_bars(bars, rates, text_color):
    for i, bar in enumerate(bars):
        val = rates[i]
        if val > 4: 
            x = bar.get_x() + bar.get_width() / 2
            y = bar.get_y() + bar.get_height() / 2
            ax.text(x, y, f"{val:.1f} %", ha='center', va='center', 
                    fontsize=12, color=text_color, fontweight='bold')

add_labels_inside_bars(bars_success, success_rates, 'white')
add_labels_inside_bars(bars_type1, type1_rates, '#333333')
add_labels_inside_bars(bars_type2, other_rates, 'white')

average_error_type23 = other_rates[-1]

# Čára a zóna v pozadí
ax.axhline(overall_rate, color=color_success, linestyle='--', linewidth=2.5, alpha=0.8, zorder=0)
ax.axhspan(100 - average_error_type23, 100, color=color_type2, alpha=0.15, zorder=0)

# Osa X
ax.set_xticks(x_pos)
ax.set_xticklabels(labels, fontsize=12, color='#444444')
for label in ax.get_xticklabels():
    text = label.get_text()
    if 'Skupina' in text or text == 'CELKOVĚ':
        label.set_fontweight('bold')

# Osa Y
ax.set_ylim(0, 100)
ax.set_yticks([0, 25, 50, 75, 100])
ax.set_yticklabels(['0 %', '25 %', '50 %', '75 %', '100 %'], color='#555555', fontsize=12)
ax.set_ylabel("Složení interakcí (%)", labelpad=15, fontweight='bold', color='#333333')
ax.set_title("Úspěšnost a typy chyb programu KAPR ze simulační studie", pad=40, fontweight='bold', color='#222222')

# ========= CELÁ LEGENDA V JEDNOM ŘÁDKU =========
leg_succ = mpatches.Patch(color=color_success, label='Úspěch (Správně)')
leg_err1 = mpatches.Patch(color=color_type1, label='Fail-Safe (Výpadek)')
leg_err2 = mpatches.Patch(color=color_type2, label='Chyba (Rizikové)')
line_overall = mlines.Line2D([], [], color=color_success, linestyle='--', linewidth=2.5, label=f'Cíl: {overall_rate:.1f} %')
# Použití mpatches.Patch pro 'Zónu', aby v legendě vypadala jako blok
rect_error = mpatches.Patch(color=color_type2, alpha=0.15, label=f'Zóna chyb: {average_error_type23:.1f} %')

# ncol=5 zajistí jeden řádek pro všechny prvky
ax.legend(handles=[leg_succ, leg_err1, leg_err2, line_overall, rect_error], 
          loc='lower center', bbox_to_anchor=(0.5, -0.28), ncol=5, frameon=False, fontsize=10)

ax.yaxis.grid(True, linestyle='-', color='#EEEEEE', alpha=0.8, zorder=0)

plt.tight_layout()
plt.savefig("graf_simulacni_studie.png", dpi=300, bbox_inches='tight')
plt.show()