import os
import json
import pandas as pd
from datetime import datetime
from collections import deque
import sys
import traceback
import logging
import ollama
from groq import Groq
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# --- LOGGING KONFIGURACE ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('ai_logic.log')
    ]
)
logger = logging.getLogger(__name__)

# --- KONFIGURACE ---
# Zde si nastav model, který chceš defaultně používat
DEFAULT_MODEL = "openai/gpt-oss-20b"  
#        "llama-3.3-70b-versatile",
#        "llama-3.1-8b-instant",
#        "openai/gpt-oss-120b",
#        "openai/gpt-oss-20b",
#        "gemini-1.5-flash",
#        "gemini-2.5-flash",
#        "gemini-2.5-flash-lite"

TEMPERATURE = 0.1

# Inicializace klientů
groq_client = None
try:
    if os.environ.get("GROQ_API_KEY"):
        groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        logger.info("✓ Groq klient úspěšně inicializován")
    else:
        logger.warning("⚠ GROQ_API_KEY není nastaven")
except Exception as e:
    logger.error(f"✗ Chyba při inicializaci Groq: {e}", exc_info=True)

try:
    if os.environ.get("GOOGLE_API_KEY"):
        genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
        logger.info("✓ Google Gemini klient úspěšně inicializován")
    else:
        logger.warning("⚠ GOOGLE_API_KEY není nastaven")
except Exception as e:
    logger.error(f"✗ Chyba při inicializaci Google Gemini: {e}", exc_info=True)

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
    try:
        if not ALL_KNOWN_ITEMS:
            logger.warning("⚠ seznam ALL_KNOWN_ITEMS je prázdný")
        items_str = ', '.join(f'"{item}"' for item in ALL_KNOWN_ITEMS)
    except Exception as e:
        logger.error(f"✗ Chyba při generování system promptu: {e}", exc_info=True)
        items_str = '"Neznámé položky"'
    return f"""
Jsi expert na extrakci lékařských dat z mluveného slova v reálném čase.
Tvým úkolem je naslouchat hlášením lékaře/záchranáře a strukturovat je do JSON formátu.
Údaje si NEVYMYŠLEJ, pokud nejsou explicitně uvedeny v textu, ponech je prázdné.
Pracuj pouze s textem v českém jazyce.

Pravidla:
1. Výstup musí být VŽDY a POUZE platný JSON objekt.
2. JSON obsahuje klíč "polozky", což je slovník.
3. Klíče ve slovníku "polozky" musí odpovídat názvům z následujícího seznamu (nebo jejich synonymům, které normalizuješ):
   [{items_str}]
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
        if not text or not isinstance(text, str):
            logger.error(f"✗ Neplatný vstup pro query_llm: {type(text)}")
            return None
            
        system_prompt = get_system_prompt()
        try:
            logger.info(f"💡 Inicializace LLM dotazu s modelem: {model_name}")
            
            # 1. Google Gemini
            if "gemini" in model_name.lower():
                try:
                    if not os.environ.get("GOOGLE_API_KEY"):
                        logger.error("✗ GOOGLE_API_KEY není nastavený")
                        return None
                    model = genai.GenerativeModel(model_name=model_name, system_instruction=system_prompt)
                    response = model.generate_content(text, generation_config={"response_mime_type": "application/json"})
                    result = json.loads(response.text)
                    logger.info(f"✓ Gemini dotaz úspěšný")
                    return result
                except json.JSONDecodeError as e:
                    logger.error(f"✗ Gemini vrátil neplatný JSON: {e}")
                    return None
                except Exception as e:
                    logger.error(f"✗ Chyba při volání Gemini API: {e}", exc_info=True)
                    return None
            
            # 2. Groq
            elif "llama" in model_name.lower() or "mixtral" in model_name.lower() or "gpt" in model_name.lower():
                try:
                    if not groq_client:
                        logger.error("✗ Groq klient není inicializován")
                        return None
                    chat = groq_client.chat.completions.create(
                        messages=[{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': text}],
                        model=model_name, temperature=TEMPERATURE, response_format={"type": "json_object"}
                    )
                    result = json.loads(chat.choices[0].message.content)
                    logger.info(f"✓ Groq dotaz s {model_name} úspěšný")
                    return result
                except json.JSONDecodeError as e:
                    logger.error(f"✗ Groq vrátil neplatný JSON: {e}")
                    return None
                except Exception as e:
                    logger.error(f"✗ Chyba při volání Groq API: {e}", exc_info=True)
                    return None

            # 3. Ollama (Lokální)
            else:
                try:
                    response = ollama.chat(
                        model=model_name,
                        messages=[{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': text}],
                        options={'temperature': TEMPERATURE, 'response_format': {'type': 'json_object'}}
                    )
                    content = response['message']['content']
                    clean_content = content.replace("```json", "").replace("```", "").strip()
                    result = json.loads(clean_content)
                    logger.info(f"✓ Ollama dotaz s {model_name} úspěšný")
                    return result
                except json.JSONDecodeError as e:
                    logger.error(f"✗ Ollama vrátil neplatný JSON: {e}")
                    return None
                except Exception as e:
                    logger.error(f"✗ Chyba při volání Ollama: {e}", exc_info=True)
                    return None

        except Exception as e:
            logger.error(f"✗ Neočekávaná chyba v query_llm: {e}", exc_info=True)
            return None

class SessionManager:
    """Třída pro správu dávkového zpracování a ukládání CSV"""
    def __init__(self):
        try:
            self.categories = ["DrABCDE", "Medication", "Interventions", "Physical Examination", "History", "SBAR", "Other"]
            self.data_tables = {}
            self.reset_tables()
            logger.info("✓ SessionManager úspěšně inicializován")
        except Exception as e:
            logger.error(f"✗ Chyba při inicializaci SessionManager: {e}", exc_info=True)
            self.categories = ["DrABCDE", "Medication", "Interventions", "Physical Examination", "History", "SBAR", "Other"]
            self.data_tables = {}
            self.reset_tables()

    def reset_tables(self):
        try:
            self.data_tables = {}
            for cat in self.categories:
                self.data_tables[cat] = pd.DataFrame(columns=['Aktuální stav'])
                self.data_tables[cat].index.name = "Položka"
            logger.debug("✓ Tabulky resetovány")
        except Exception as e:
            logger.error(f"✗ Chyba při resetování tabulek: {e}", exc_info=True)

    def determine_category(self, item_name):
        try:
            item_lower = item_name.lower()
            for cat, keywords in CATEGORY_DEFAULTS.items():
                for kw in keywords:
                    if kw in item_lower:
                        logger.debug(f"📂 Položka '{item_name}' zařazena do '{cat}'")
                        return cat
            logger.debug(f"📂 Položka '{item_name}' zařazena do 'Other'")
            return "Other"
        except Exception as e:
            logger.error(f"✗ Chyba v determine_category: {e}")
            return "Other"

    def process_data_into_tables(self, json_data, timestamp_str):
        try:
            if not json_data:
                logger.warning("⚠ JSON data jsou None nebo prázdná")
                return
            
            if 'polozky' not in json_data:
                logger.warning("⚠ Klíč 'polozky' nebyl nalezen v JSON datech")
                return

            processed_count = 0
            for item_name, value in json_data['polozky'].items():
                try:
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
                        logger.debug(f"↻ Aktualizován: {item_name} = {value}")
                    else:
                        # Nový řádek (používáme pd.concat, append je deprecated)
                        new_row = pd.DataFrame([[str(value)]], columns=[timestamp_str], index=[item_name])
                        self.data_tables[category] = pd.concat([self.data_tables[category], new_row])
                        logger.debug(f"✓ Přidán nový záznam: {item_name} = {value}")
                    processed_count += 1
                except Exception as e:
                    logger.error(f"✗ Chyba při zpracování položky '{item_name}': {e}")
                    continue
            
            logger.info(f"✓ Zpracováno {processed_count} položek do tabulek")
        except Exception as e:
            logger.error(f"✗ Kritická chyba v process_data_into_tables: {e}", exc_info=True)

    def save_session(self):
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            sessions_dir = os.path.join(base_dir, 'sessions')
            
            try:
                if not os.path.exists(sessions_dir):
                    os.makedirs(sessions_dir)
                    logger.info(f"✓ Vytvořen adresář sessions: {sessions_dir}")
            except OSError as e:
                logger.error(f"✗ Nelze vytvořit adresář sessions: {e}")
                return None, []
            
            timestamp_folder = datetime.now().strftime('Session_%Y%m%d_%H%M%S')
            current_session_dir = os.path.join(sessions_dir, timestamp_folder)
            
            try:
                os.makedirs(current_session_dir, exist_ok=True)
                logger.info(f"✓ Vytvořen adresář relace: {current_session_dir}")
            except OSError as e:
                logger.error(f"✗ Nelze vytvořit adresář relace: {e}")
                return None, []
            
            saved_files = []
            files_count = 0
            
            for category, df in self.data_tables.items():
                try:
                    # Uložit jen pokud má data (více než 1 sloupec = 'Aktuální stav' + časy)
                    if not df.empty and len(df.columns) > 1:
                        safe_cat_name = category.replace(" ", "_")
                        csv_path = os.path.join(current_session_dir, f'vysledny_stav_{safe_cat_name}.csv')
                        
                        try:
                            # Ukládáme se středníkem, aby to Excel v ČR otevřel správně
                            df.to_csv(csv_path, sep=';', encoding='utf-8')
                            saved_files.append(os.path.basename(csv_path))
                            logger.info(f"✓ Uložen soubor: {os.path.basename(csv_path)}")
                            files_count += 1
                        except Exception as e:
                            logger.error(f"✗ Nelze uložit soubor {csv_path}: {e}")
                            continue
                except Exception as e:
                    logger.error(f"✗ Chyba při zpracování kategorie {category}: {e}")
                    continue
            
            if files_count == 0:
                logger.warning(f"⚠ Žádné soubory nebyly uloženy (možná nejsou data)")
            else:
                logger.info(f"✓ Relace úspěšně uložena: {files_count} souborů v {current_session_dir}")
            return current_session_dir, saved_files
            
        except Exception as e:
            logger.error(f"✗ Kritická chyba v save_session: {e}", exc_info=True)
            return None, []