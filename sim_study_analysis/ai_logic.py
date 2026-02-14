import os
import json
import pandas as pd
from datetime import datetime
from collections import deque
import ollama
from groq import Groq
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# --- KONFIGURACE ---
# Zde si nastav model, který chceš defaultně používat
DEFAULT_MODEL = "gemma2:9b"  # nebo "llama-3.3-70b-versatile", "gemini-2.0-flash"
TEMPERATURE = 0.1

# Inicializace klientů
groq_client = None
try:
    if os.environ.get("GROQ_API_KEY"):
        groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
except Exception as e:
    print(f"Groq warning: {e}")

if os.environ.get("GOOGLE_API_KEY"):
    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

# --- DATA: SYNONYMA A MAPPING (Zkopírováno z tvého kódu) ---
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

# Jednoduché mapování pro určení tabulky (Lze rozšířit)
CATEGORY_DEFAULTS = {
    "DrABCDE": ["srdeční frekvence", "krevní tlak", "spo2", "dechová frekvence", "avpu", "kapilární návrat", "teplota", "glykemie"],
    "Medication": ["adrenalin", "amiodaron", "atropin", "noradrenalin", "adenosin", "midazolam", "fentanyl", "morfin", "ketamin", "propofol", "aspirin (asa)", "heparin", "nitroglycerin (isoket)", "exacyl"],
    "Interventions": ["intubace", "kpr", "defibrilace", "přístup", "io", "iv"],
    "SBAR": ["sbar", "report"],
    "History": ["alergie", "anamnéza", "léky doma"]
}

ALL_KNOWN_ITEMS = list(set(ITEM_SYNONYMS.values()))

def get_system_prompt():
    items_str = ', '.join(f'"{item}"' for item in ALL_KNOWN_ITEMS)
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

class AIService:
    @staticmethod
    def query_llm(text, model_name=DEFAULT_MODEL):
        system_prompt = get_system_prompt()
        try:
            # 1. Google Gemini
            if "gemini" in model_name.lower():
                model = genai.GenerativeModel(model_name=model_name, system_instruction=system_prompt)
                response = model.generate_content(text, generation_config={"response_mime_type": "application/json"})
                return json.loads(response.text)
            
            # 2. Groq
            elif "llama" in model_name.lower() or "mixtral" in model_name.lower() or "gpt" in model_name.lower():
                if not groq_client: return None
                chat = groq_client.chat.completions.create(
                    messages=[{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': text}],
                    model=model_name, temperature=TEMPERATURE, response_format={"type": "json_object"}
                )
                return json.loads(chat.choices[0].message.content)

            # 3. Ollama (Lokální)
            else:
                response = ollama.chat(
                    model=model_name,
                    messages=[{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': text}],
                    options={'temperature': TEMPERATURE, 'response_format': {'type': 'json_object'}}
                )
                content = response['message']['content']
                clean_content = content.replace("```json", "").replace("```", "").strip()
                return json.loads(clean_content)

        except Exception as e:
            print(f"LLM Error ({model_name}): {e}")
            return None

class SessionManager:
    """Třída pro správu dávkového zpracování a ukládání CSV"""
    def __init__(self):
        self.categories = ["DrABCDE", "Medication", "Interventions", "Physical Examination", "History", "SBAR", "Other"]
        self.data_tables = {}
        self.reset_tables()

    def reset_tables(self):
        self.data_tables = {}
        for cat in self.categories:
            self.data_tables[cat] = pd.DataFrame(columns=['Aktuální stav'])
            self.data_tables[cat].index.name = "Položka"

    def determine_category(self, item_name):
        item_lower = item_name.lower()
        for cat, keywords in CATEGORY_DEFAULTS.items():
            for kw in keywords:
                if kw in item_lower:
                    return cat
        return "Other"

    def process_data_into_tables(self, json_data, timestamp_str):
        if not json_data or 'polozky' not in json_data:
            return

        for item_name, value in json_data['polozky'].items():
            item_lower = item_name.lower()
            
            # Normalizace
            if item_lower in ITEM_SYNONYMS:
                item_name = ITEM_SYNONYMS[item_lower]
                item_lower = item_name.lower()
            
            # Kategorie
            category = self.determine_category(item_name)
            df = self.data_tables[category]
            
            # Přidání sloupce času
            if timestamp_str not in df.columns:
                df[timestamp_str] = ""
            
            # Zápis
            if item_name in df.index:
                df.loc[item_name, timestamp_str] = str(value)
            else:
                # Nový řádek (používáme pd.concat, append je deprecated)
                new_row = pd.DataFrame([[str(value)]], columns=[timestamp_str], index=[item_name])
                self.data_tables[category] = pd.concat([self.data_tables[category], new_row])

    def save_session(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        sessions_dir = os.path.join(base_dir, 'sessions')
        if not os.path.exists(sessions_dir):
            os.makedirs(sessions_dir)
            
        timestamp_folder = datetime.now().strftime('Session_%Y%m%d_%H%M%S')
        current_session_dir = os.path.join(sessions_dir, timestamp_folder)
        os.makedirs(current_session_dir, exist_ok=True)
        
        saved_files = []
        for category, df in self.data_tables.items():
            # Uložit jen pokud má data (více než 1 sloupec = 'Aktuální stav' + časy)
            if not df.empty and len(df.columns) > 1:
                safe_cat_name = category.replace(" ", "_")
                csv_path = os.path.join(current_session_dir, f'vysledny_stav_{safe_cat_name}.csv')
                # Ukládáme se středníkem, aby to Excel v ČR otevřel správně
                df.to_csv(csv_path, sep=';', encoding='utf-8')
                saved_files.append(os.path.basename(csv_path))
                
        return current_session_dir, saved_files