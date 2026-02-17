import csv
import json
import os
import sys
from datetime import datetime

def get_input_path(prompt_text):
    """
    Interaktivní získání cesty k souboru s odstraněním uvozovek.
    """
    print(f"\n{prompt_text}")
    path = input("Cesta: ").strip()
    return path.strip('"\'')

def get_start_time():
    """
    Získá od uživatele počáteční čas nahrávání.
    """
    print("\n--- Nastavení času ---")
    print("Zadejte přesný čas začátku nahrávání (Čas, kdy v JSONu běží sekunda 0.0).")
    print("Formát: YYYY-MM-DD HH:MM:SS (např. 2026-01-14 14:45:30)")
    
    while True:
        time_str = input("Startovní čas: ").strip()
        try:
            # Zkusíme parsovat čas
            dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            return dt
        except ValueError:
            print("Chybný formát! Zkuste to znovu přesně ve formátu YYYY-MM-DD HH:MM:SS")

def merge_csv_and_json(csv_path, json_path, output_path, start_time):
    # 1. Načtení JSON dat
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
            # Pokud je JSON list, seřadíme ho pro jistotu podle startu
            if isinstance(json_data, list):
                json_data.sort(key=lambda x: x.get('start', 0))
            else:
                print("CHYBA: JSON soubor musí obsahovat seznam (list) objektů.")
                return
    except Exception as e:
        print(f"Chyba při čtení JSON: {e}")
        return

    # 2. Načtení CSV dat
    csv_rows = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Předpokládáme středník jako oddělovač z předchozího skriptu
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                csv_rows.append(row)
    except Exception as e:
        print(f"Chyba při čtení CSV: {e}")
        return

    if not csv_rows:
        print("CSV soubor je prázdný.")
        return

    print(f"\nZpracovávám {len(csv_rows)} řádků z CSV a {len(json_data)} segmentů z JSON...")

    # 3. Zpracování a párování
    merged_rows = []
    
    # Formát času v CSV (z předchozího log parseru)
    csv_time_format = "%Y-%m-%d %H:%M:%S"

    for i in range(len(csv_rows)):
        current_row = csv_rows[i]
        
        # Získání času aktuálního řádku
        try:
            current_time_str = current_row['Čas'] # Pozor na název sloupce z předchozího skriptu
            current_dt = datetime.strptime(current_time_str, csv_time_format)
        except ValueError:
            # Pokud čas chybí nebo je špatný, přeskočíme párování JSONu, ale řádek zachováme
            current_row['JSON Text'] = ""
            merged_rows.append(current_row)
            continue

        # Výpočet relativního startu v sekundách od počátku nahrávání
        rel_start_seconds = (current_dt - start_time).total_seconds()

        # Určení konce intervalu (čas následujícího řádku v CSV)
        rel_end_seconds = float('inf') # Pro poslední řádek nekonečno
        
        if i < len(csv_rows) - 1:
            try:
                next_time_str = csv_rows[i+1]['Čas']
                next_dt = datetime.strptime(next_time_str, csv_time_format)
                rel_end_seconds = (next_dt - start_time).total_seconds()
            except ValueError:
                pass # Pokud je další čas vadný, necháme nekonečno

        # Filtrace JSON segmentů, které spadají do intervalu [rel_start, rel_end)
        matching_texts = []
        for segment in json_data:
            seg_start = segment.get('start', 0)
            
            # Podmínka: Segment začíná v našem intervalu
            if rel_start_seconds <= seg_start < rel_end_seconds:
                matching_texts.append(segment.get('text', '').strip())

        # Spojení nalezených textů
        json_text_content = " ".join(matching_texts)
        
        # Přidání do řádku
        current_row['JSON Text'] = json_text_content
        merged_rows.append(current_row)

    # 4. Uložení výsledku
    fieldnames = list(csv_rows[0].keys()) # Klíče z původního CSV + 'JSON Text' už tam je díky přídavku
    
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            writer.writerows(merged_rows)
        
        print("-" * 30)
        print(f"HOTOVO! Sloučený soubor uložen zde:\n{output_path}")
        
    except Exception as e:
        print(f"Chyba při zápisu CSV: {e}")

if __name__ == "__main__":
    print("=== MERGE TOOL: CSV (Logy) + JSON (Audio) ===")
    
    # 1. Získání cest
    csv_file = get_input_path("1. Přetáhněte sem CSV soubor (výstup z parseru):")
    if not os.path.isfile(csv_file):
        print("CSV soubor neexistuje.")
        sys.exit()

    json_file = get_input_path("2. Přetáhněte sem JSON soubor (merged_output.json):")
    if not os.path.isfile(json_file):
        print("JSON soubor neexistuje.")
        sys.exit()

    # 2. Získání startovního času
    start_time_ref = get_start_time()

    # 3. Příprava výstupní cesty
    dir_name = os.path.dirname(csv_file)
    base_name = os.path.splitext(os.path.basename(csv_file))[0]
    output_file = os.path.join(dir_name, f"{base_name}_with_audio.csv")

    # 4. Spuštění
    merge_csv_and_json(csv_file, json_file, output_file, start_time_ref)

    input("\nStiskněte Enter pro ukončení...")