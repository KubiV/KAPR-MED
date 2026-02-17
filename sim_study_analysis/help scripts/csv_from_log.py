import re
import csv
import os
import sys

def get_input_path():
    """
    Získá cestu k souboru buď z argumentů příkazové řádky,
    nebo interaktivně od uživatele.
    """
    if len(sys.argv) > 1:
        # Pokud byl soubor předán jako argument (např. přetažením na skript)
        fpath = sys.argv[1]
    else:
        # Interaktivní vstup
        print("--- Parser Logů do CSV ---")
        fpath = input("Zadejte cestu k souboru (nebo ho sem přetáhněte): ").strip()
    
    # Odstranění uvozovek, které některé terminály přidávají při Drag&Drop
    return fpath.strip('"\'')

def parse_log(input_path):
    # Kontrola existence souboru
    if not os.path.isfile(input_path):
        print(f"CHYBA: Soubor '{input_path}' neexistuje.")
        return

    # 1. Příprava výstupní cesty (stejná složka, stejný název + _parsed.csv)
    directory = os.path.dirname(input_path)
    filename = os.path.basename(input_path)
    name, ext = os.path.splitext(filename)
    output_filename = f"{name}_parsed.csv"
    output_path = os.path.join(directory, output_filename)

    print(f"Načítám: {filename}")
    print(f"Cíl: {output_filename}")

    # 2. Regulární výrazy
    # Čas: YYYY-MM-DD HH:MM:SS
    re_time = r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
    # Přepis: Hledá slovo PŘEPIS v hranatých závorkách a bere zbytek řádku
    re_transcription = r"INFO - \[.*? PŘEPIS\]\s*(.*)"
    # Data: Hledá JSON za frází "LLM extrahoval data:"
    re_data = r"INFO - LLM extrahoval data:\s*(\{.*\})"

    rows = []
    current_entry = None

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # --- Hledání PŘEPISU ---
                trans_match = re.search(re_transcription, line)
                if trans_match:
                    # Získání času
                    time_match = re.search(re_time, line)
                    timestamp = time_match.group(1) if time_match else "Neznámý čas"
                    
                    text = trans_match.group(1).strip()
                    
                    # Vytvoření nového řádku
                    current_entry = {
                        "timestamp": timestamp,
                        "text": text,
                        "data": "" # Zatím prázdné
                    }
                    rows.append(current_entry)
                    continue

                # --- Hledání DAT (přiřadí se k poslednímu přepisu) ---
                data_match = re.search(re_data, line)
                if data_match and current_entry:
                    # Pokud najdeme data a máme otevřený záznam
                    current_entry["data"] = data_match.group(1)

        # 3. Uložení do CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            
            # Hlavička
            writer.writerow(['Čas', 'Přepsaný text', 'Extrahovaná data'])
            
            for row in rows:
                writer.writerow([row["timestamp"], row["text"], row["data"]])

        print("-" * 30)
        print(f"HOTOVO! Výsledek uložen do:\n{output_path}")
        print(f"Počet záznamů: {len(rows)}")

    except Exception as e:
        print(f"Došlo k neočekávané chybě: {e}")

if __name__ == "__main__":
    path = get_input_path()
    if path:
        parse_log(path)
    
    # Aby se okno nezavřelo hned po skončení (pokud běží na Windows poklepáním)
    input("\nStiskněte Enter pro ukončení...")