import json
import os

def get_files_from_user():
    """Získá seznam souborů od uživatele přes terminál."""
    files = []
    print("--- Zadávání souborů ---")
    print("Zadávejte cesty k souborům JSON v pořadí, v jakém mají jít za sebou.")
    print("Výsledný soubor se uloží do složky, kde se nachází PRVNÍ zadaný soubor.")
    print("Pro ukončení zadávání stiskněte ENTER bez napsání textu.")
    print("-" * 30)

    counter = 1
    while True:
        # Vstup od uživatele
        user_input = input(f"Zadejte cestu k souboru č. {counter} (nebo ENTER pro konec): ").strip()
        
        # Odstranění uvozovek, pokud je uživatel zadal (např. při kopírování cesty ve Windows)
        file_path = user_input.replace('"', '').replace("'", "")
        
        if not file_path:
            if len(files) < 1:
                print("Musíte zadat alespoň jeden soubor.")
                continue
            break

        if os.path.isfile(file_path):
            # Uložíme absolutní cestu pro jistotu
            abs_path = os.path.abspath(file_path)
            files.append(abs_path)
            print(f"   OK: {os.path.basename(abs_path)}")
            counter += 1
        else:
            print(f"   Chyba: Soubor '{file_path}' nebyl nalezen. Zkuste to znovu.")
            
    return files

def merge_transcripts(file_list):
    """Spojí transkripty a přepočítá časy."""
    merged_data = []
    current_time_offset = 0.0
    
    print(f"\nZpracovávám {len(file_list)} souborů...")

    for index, file_path in enumerate(file_list):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Pokud je JSON list (očekávaný formát)
            if not isinstance(data, list):
                # Zkusíme najít klíč 'segments', pokud je to dict
                if isinstance(data, dict) and "segments" in data:
                    data = data["segments"]
                else:
                    print(f"Varování: Soubor {os.path.basename(file_path)} nemá podporovanou strukturu. Přeskakuji.")
                    continue

            # Zjištění trvání aktuálního souboru (poslední end time)
            file_duration = 0.0
            if data:
                last_segment = data[-1]
                file_duration = last_segment.get('end', 0)

            print(f" -> Část {index + 1}: {os.path.basename(file_path)}")
            print(f"    Posun času: +{current_time_offset:.2f}s")
            
            # Úprava časů a ID v aktuálním souboru
            for segment in data:
                # Upravíme ID, aby navazovala
                segment['id'] = len(merged_data)
                
                # Přičtení offsetu k časům
                if 'start' in segment:
                    segment['start'] += current_time_offset
                if 'end' in segment:
                    segment['end'] += current_time_offset
                
                # Oprava 'seek' pokud je potřeba (volitelné, záleží na použití)
                # if 'seek' in segment: segment['seek'] += int(current_time_offset * 100)

                merged_data.append(segment)

            # Aktualizace offsetu pro PŘÍŠTÍ soubor
            # Offset se zvyšuje o délku aktuálního souboru
            # POZOR: Pokud máte přesnou délku audia, je lepší ji zadat ručně, 
            # ale zde bereme konec posledního titulku jako konec souboru.
            current_time_offset = merged_data[-1]['end'] if merged_data else 0.0
            
        except Exception as e:
            print(f"Chyba při zpracování souboru {file_path}: {e}")
            return None

    return merged_data

def clean_data(data):
    """Odstraní nepotřebné klíče, nechá jen start, end a text."""
    cleaned = []
    for segment in data:
        # Vytvoříme nový slovník jen s vybranými klíči
        new_segment = {
            "start": segment.get("start"),
            "end": segment.get("end"),
            "text": segment.get("text", "").strip()
        }
        cleaned.append(new_segment)
    return cleaned

def main():
    files = get_files_from_user()
    
    if not files:
        print("Ukončuji program.")
        return

    # 1. Spojení a přepočet časů
    result_data = merge_transcripts(files)
    
    if result_data is None:
        print("Došlo k chybě při spojování.")
        return

    # 2. Volitelné čištění dat
    print("\n--- Možnosti výstupu ---")
    choice = input("Chcete JSON vyčistit (zachovat jen start, end, text)? (ano/ne) [ne]: ").strip().lower()
    
    if choice in ['ano', 'y', 'yes', 'a']:
        result_data = clean_data(result_data)
        print("Data vyčištěna.")
    else:
        print("Data ponechána v původní struktuře.")

    # 3. Určení cesty pro uložení
    # Vezmeme cestu prvního souboru
    first_file_path = files[0]
    # Získáme adresář, ve kterém je první soubor
    output_directory = os.path.dirname(first_file_path)
    # Vytvoříme cestu k novému souboru v tomtéž adresáři
    output_filename = os.path.join(output_directory, "merged_output.json")

    # 4. Uložení
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)
        
        print("\n" + "="*40)
        print("HOTOVO!")
        print(f"Soubor byl uložen zde:\n{output_filename}")
        print("="*40)
        
    except Exception as e:
        print(f"Chyba při ukládání souboru: {e}")
        # Záloha - pokus o uložení do aktuálního adresáře, pokud ten cílový selže (např. práva zápisu)
        try:
            fallback_name = "merged_output_backup.json"
            with open(fallback_name, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, indent=2, ensure_ascii=False)
            print(f"Zápis do původní složky selhal. Uloženo do {fallback_name} v aktuální složce skriptu.")
        except:
            pass

if __name__ == "__main__":
    main()