import json
import os

def merge_subtitles(input_file, output_file, n):
    """
    Sloučí po sobě jdoucí titulky do skupin po 'n'.
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        merged_data = []
        
        for i in range(0, len(data), n):
            chunk = data[i : i + n]
            if not chunk: continue
            
            new_entry = chunk[0].copy()
            new_entry['text'] = "".join([item.get('text', '') for item in chunk])
            new_entry['end'] = chunk[-1]['end']
            
            if 'tokens' in new_entry:
                all_tokens = []
                for item in chunk:
                    all_tokens.extend(item.get('tokens', []))
                new_entry['tokens'] = all_tokens
            
            merged_data.append(new_entry)
            
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=2)
            
        print(f"\n✅ Hotovo!")
        print(f"   Vstup:  {os.path.basename(input_file)}")
        print(f"   Výstup: {os.path.basename(output_file)}")
        print(f"   Uloženo v: {os.path.dirname(output_file)}")
        
    except Exception as e:
        print(f"\n❌ Nastala chyba: {e}")

def get_input_path():
    """Získá cestu k souboru od uživatele a očistí ji od uvozovek."""
    path = input("📂 Přetáhni JSON soubor do terminálu (nebo vlož cestu): ").strip()
    # Odstranění uvozovek, které terminál někdy přidává
    return path.strip('"').strip("'")

# --- Interaktivní spuštění ---
if __name__ == "__main__":
    print("--- Slučovač JSON titulků ---")
    
    # 1. Získání cesty k souboru
    input_path = get_input_path()
    
    if os.path.isfile(input_path):
        # 2. Získání parametru N
        try:
            n_input = input("🔢 Kolik řádků sloučit? (výchozí: 2): ").strip()
            n = int(n_input) if n_input else 2 # Pokud uživatel jen odentruje, použije se 2
        except ValueError:
            print("Neplatné číslo, použiji výchozí hodnotu 2.")
            n = 2

        # 3. Vypočítání cesty pro uložení
        # Získáme adresář a název původního souboru bez přípony
        directory = os.path.dirname(input_path)
        filename_without_ext = os.path.splitext(os.path.basename(input_path))[0]
        
        # Vytvoříme nový název: puvodni_sloucene_n4.json
        new_filename = f"{filename_without_ext}_sloucene_n{n}.json"
        
        # Složíme kompletní cestu zpět do stejného adresáře
        output_path = os.path.join(directory, new_filename)

        # 4. Spuštění
        merge_subtitles(input_path, output_path, n)
        
    else:
        print(f"\n❌ Soubor nebyl nalezen: {input_path}")
    
    input("\nStiskni Enter pro ukončení...")