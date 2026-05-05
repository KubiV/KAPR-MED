import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import textwrap

# 1. Načtení dat
df = pd.read_csv('survey_data.csv')

# 2. Sjednocení profesí
def clean_profession(prof):
    prof = str(prof).lower()
    if 'záchranář' in prof: return 'Záchranář'
    if 'lékař' in prof: return 'Lékař'
    return None

df['Skupina'] = df['Profese'].apply(clean_profession)
df = df[df['Skupina'].notna()]

# 3. Definice otázek a jejich popisků na osách
# Klíč: kus textu z CSV, Hodnota: (Celá otázka, Popis Y=1, Popis Y=10)
questions_config = [
    {
        'key': 'znepokojovalo nahrávání',
        'full_title': 'Jak moc by vás znepokojovalo nahrávání mluveného slova během zásahu?',
        'y_min': '1: Velice znepokojovalo',
        'y_max': '10: Neznepokojovalo'
    },
    {
        'key': 'přijatelný poslech AI',
        'full_title': 'Jak moc by byl pro vás přijatelný poslech AI zařízením bez uchování zvukového záznamu? (uchování pouze extrahovaných dat)',
        'y_min': '1: Přijatelný',
        'y_max': '10: Nepřijatelný'
    },
    {
        'key': 'znepokojivé být nahrávaný',
        'full_title': 'Jak moc je pro vás znepokojivé být nahrávaný v průběhu výkonu?',
        'y_min': '1: Nejméně znepokojivé',
        'y_max': '10: Nejvíce znepokojivé'
    }
]

# 4. Vizuální nastavení
fig, axes = plt.subplots(3, 1, figsize=(11, 18))
colors = {'Lékař': '#3498db', 'Záchranář': '#e74c3c'}

for i, config in enumerate(questions_config):
    # Najít sloupec v DF
    actual_col = next((c for c in df.columns if config['key'] in c), None)
    
    if actual_col:
        df[actual_col] = pd.to_numeric(df[actual_col], errors='coerce')
        
        # Sloupcový graf (průměry)
        sns.barplot(
            data=df, x='Skupina', y=actual_col, ax=axes[i], 
            palette=colors, alpha=0.5, errorbar=None
        )
        
        # Jednotlivé odpovědi (body)
        sns.stripplot(
            data=df, x='Skupina', y=actual_col, ax=axes[i], 
            palette=colors, size=9, jitter=True, edgecolor='black', linewidth=0.5
        )
        
        # Formátování nadpisu (zalomení dlouhého textu)
        wrapped_title = "\n".join(textwrap.wrap(config['full_title'], width=80))
        axes[i].set_title(wrapped_title, fontsize=13, fontweight='bold', pad=15)
        
        # Nastavení osy Y
        axes[i].set_ylim(0, 11.5)
        axes[i].set_yticks(range(1, 11))
        axes[i].set_ylabel('Škála hodnocení')
        axes[i].set_xlabel('')
        
        # Přidání popisků extrémů přímo k ose
        axes[i].annotate(config['y_min'], xy=(-0.45, 1), color='darkred', fontsize=10, fontweight='bold')
        axes[i].annotate(config['y_max'], xy=(-0.45, 10), color='darkgreen', fontsize=10, fontweight='bold')

        # Průměrné hodnoty číslem
        means = df.groupby('Skupina')[actual_col].mean()
        for j, skupina in enumerate(['Lékař', 'Záchranář']):
            if skupina in means:
                axes[i].text(j, means[skupina] + 0.3, f"Průměr: {means[skupina]:.1f}", 
                             ha='center', va='bottom', fontweight='bold', bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))

plt.tight_layout(rect=[0, 0.03, 1, 0.95])
plt.show()