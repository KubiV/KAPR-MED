import json

def merge_subtitles(input_file, output_file, n):
    """
    Sloučí po sobě jdoucí titulky do skupin po 'n'.
    Zachová ID a start z prvního, end z posledního, texty spojí.
    """
    try:
        # Načtení JSON souboru
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        merged_data = []
        
        # Procházíme data po blocích o velikosti n
        for i in range(0, len(data), n):
            chunk = data[i : i + n]
            
            if not chunk:
                continue
            
            # 1. Základ (info a čas začátku) vezmeme z prvního titulku ve skupině
            new_entry = chunk[0].copy()
            
            # 2. Texty spojíme za sebe (v datech už jsou mezery, takže jen spojíme)
            combined_text = "".join([item.get('text', '') for item in chunk])
            new_entry['text'] = combined_text
            
            # 3. Čas konce musíme vzít z posledního titulku, 
            # jinak by titulek zmizel dříve, než se text dořekne.
            new_entry['end'] = chunk[-1]['end']
            
            # 4. (Volitelné) Spojíme i tokeny, pokud je potřebujete pro další zpracování
            if 'tokens' in new_entry:
                all_tokens = []
                for item in chunk:
                    all_tokens.extend(item.get('tokens', []))
                new_entry['tokens'] = all_tokens
            
            merged_data.append(new_entry)
            
        # Uložení výsledku do nového souboru
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=2)
            
        print(f"Hotovo! Sloučeno po {n}. Výsledek uložen do '{output_file}'.")
        
    except Exception as e:
        print(f"Nastala chyba: {e}")

# --- Nastavení ---
input_filename = 'Untitled.json'  # Váš vstupní soubor
n = 4                             # Počet titulků ke sloučení (změňte na 2, 3, atd.)
output_filename = f'sloucene_titulky_n{n}.json'

# Spuštění funkce
if __name__ == "__main__":
    merge_subtitles(input_filename, output_filename, n)