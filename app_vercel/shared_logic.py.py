import os
import json
import logging
import pandas as pd
from datetime import datetime

# --- SPOLEČNÉ KONFIGURACE ---
# --- 1. KROK - SYNONYMA ---
ITEM_SYNONYMS = {
    # Původní synonyma pro Vitals
    "tepová frekvence": "Srdeční frekvence", "typová frekvence": "Srdeční frekvence", 
    "tep": "Srdeční frekvence", "puls": "Srdeční frekvence", "sf": "Srdeční frekvence", 
    "tf": "Srdeční frekvence", "srdeční frekvence (sf)": "Srdeční frekvence",
    "tlak": "Krevní tlak", "tk": "Krevní tlak", "systolický tlak": "Krevní tlak",
    "saturace": "SpO2", "sat": "SpO2", "spo2": "SpO2",
    "dech": "Dechová frekvence", "df": "Dechová frekvence",
    "vědomí": "AVPU", "gcs": "glasgow coma scale", "avpu": "AVPU", "glasgow coma scale": "gcs",
    "CRT": "Kapilární návrat", "crt": "Kapilární návrat",

    # --- NOVÉ: Synonyma pro Léčiva (Medication.csv) ---
    "adrenalin": "Adrenalin",
    "amiodaron": "Amiodaron",
    "atropin": "Atropin",
    "noradrenalin": "Noradrenalin",
    "adenosin": "Adenosin",
    "midazolam": "Midazolam",
    "fentanyl": "Fentanyl",
    "morfin": "Morfin",
    "ketamin": "Ketamin",
    "propofol": "Propofol",
    "sufentanil": "Sufentanil",
    "rokuronium": "Rokuronium",
    "sukcinylcholin": "Sukcinylcholin",
    
    # Složené názvy (Generikum vs Obchodní název)
    "aspirin": "Aspirin (ASA)", 
    "asa": "Aspirin (ASA)",
    
    "heparin": "Heparin",
    
    "nitroglycerin": "Nitroglycerin (Isoket)", 
    "isoket": "Nitroglycerin (Isoket)",
    
    "furosemid": "Furosemid",
    
    "salbutamol": "Salbutamol (Ventolin)", 
    "ventolin": "Salbutamol (Ventolin)",
    
    "urapidil": "Urapidil (Ebrantil)", 
    "ebrantil": "Urapidil (Ebrantil)",
    
    "exacyl": "Exacyl (Kys. tranexamová)", 
    "kys. tranexamová": "Exacyl (Kys. tranexamová)",
    "kyselina tranexamová": "Exacyl (Kys. tranexamová)",
    
    "magnesium sulfát": "Magnesium sulfát",
    "magnesium": "Magnesium sulfát",
    
    "naloxon": "Naloxon",
    
    "flumazenil": "Flumazenil (Anexate)", 
    "anexate": "Flumazenil (Anexate)",
    
    "glukóza": "Glukóza (G40%)", 
    "g40%": "Glukóza (G40%)",
    "g40": "Glukóza (G40%)",
    
    "paracetamol": "Paracetamol",
    "ondansetron": "Ondansetron",
    "ceftriaxon": "Ceftriaxon"
}

# --- 2. KROK - MAPPING NA DISPLEJ ---
VITALS_MAPPING = {
    "srdeční frekvence": "TF", 
    "krevní tlak": "TK", 
    "dechová frekvence": "DF",
    "spo2": "SpO2", 
    "kapilární návrat": "CRT", 
    "avpu": "AVPU"
}

def get_system_prompt(all_known_items):
    items_list_str = ', '.join(f'"{item}"' for item in all_known_items)
    return f"""
Jsi expert na extrakci lékařských dat z mluveného slova v reálném čase.
Tvým úkolem je naslouchat hlášením lékaře/záchranáře a strukturovat je do JSON formátu.
Údaje si NEVYMYŠLEJ, pokud nejsou explicitně uvedeny v textu, ponech je prázdné.
Pracuj pouze s textem v českém jazyce.

Pravidla:
1. Výstup musí být VŽDY a POUZE platný JSON objekt.
2. JSON obsahuje klíč "polozky", což je slovník.
3. Klíče ve slovníku "polozky" musí odpovídat názvům z následujícího seznamu (nebo jejich synonymům, které normalizuješ):
   [{items_list_str}]
4. Normalizuj synonyma na oficiální názvy (např. "tep" -> "Srdeční frekvence", "saturace" -> "SpO2", "Isoket" -> "Nitroglycerin (Isoket)").
5. Pokud narazíš na položku, která v seznamu není, ale je lékařsky relevantní, zahrň ji také pod jejím obvyklým názvem.
6. Hodnoty extrahuj jako čísla nebo formátovaný string (např. "120/80").

Příklady:
Uživatel: "Pacient má saturaci 92 a tlak 130 na 80. Podán Isoket jeden vstřik."
Výstup: {{"polozky": {{"SpO2": "92", "Krevní tlak": "130/80", "Nitroglycerin (Isoket)": "1 vstřik"}}}}
"""

# --- UNIVERZÁLNÍ FUNKCE PRO ZPRACOVÁNÍ DAT ---
def process_extracted_json(extracted_data, data_tables, item_mapping, current_vitals, recent_updates, all_known_items):
    """
    Tato funkce vezme JSON z AI a rozdistribuuje ho do tabulek a vitálů.
    Vrací upravené objekty.
    """
    timestamp = datetime.now().strftime('%H:%M:%S')
    
    if 'polozky' in extracted_data:
        for item_name, value in extracted_data['polozky'].items():
            item_lower = item_name.lower()
            
            # 1. Normalizace synonym
            if item_lower in ITEM_SYNONYMS:
                item_name = ITEM_SYNONYMS[item_lower]
                item_lower = item_name.lower()

            # 2. Update vitálních funkcí (pro dashboard)
            vital_key = VITALS_MAPPING.get(item_lower)
            if vital_key:
                current_vitals[vital_key] = str(value)

            # 3. Update historie
            recent_updates.appendleft(f"{timestamp} - {item_name} - {value}")
            
            # 4. Zařazení do tabulky (DrABCDE, Medication, atd.)
            category = item_mapping.get(item_lower, "Other")
            
            # Pokud kategorie neexistuje, vytvoříme v "Other"
            if category not in data_tables:
                data_tables["Other"] = pd.DataFrame(columns=['Aktuální stav'], index=[])
                data_tables["Other"].index.name = "Položka"

            df = data_tables[category]
            if timestamp not in df.columns:
                df[timestamp] = ""

            if item_name in df.index:
                df.loc[item_name, timestamp] = str(value)
            else:
                # Přidání nové položky za běhu
                new_row = pd.DataFrame([[str(value)]], columns=[timestamp], index=[item_name])
                data_tables[category] = pd.concat([data_tables[category], new_row])
                item_mapping[item_lower] = category
                all_known_items.append(item_name)

    return data_tables, current_vitals, recent_updates