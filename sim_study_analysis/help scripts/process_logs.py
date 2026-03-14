import pandas as pd
import re
from datetime import datetime
import glob
import os

def parse_log_line(line):
    # Regulární výraz pro formát: YYYY-MM-DD HH:MM:SS,ms - LEVEL - Message
    match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ - (\w+) - (.*)', line)
    if match:
        timestamp_str, level, message = match.groups()
        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        return timestamp, level, message
    return None, None, None

def is_api_error(level, message):
    # Považujeme za chybu, pokud je LEVEL = ERROR
    if level == 'ERROR':
        return True
    # Nebo pokud zpráva obsahuje HTTP request, který neskončil "200 OK" 
    if 'HTTP Request:' in message:
        # Hledá status kód, např. "HTTP/1.1 500" nebo podobné chyby
        if not re.search(r'"HTTP/1\.1 200 OK"', message):
            return True
    # Případně další explicitní chybové hlášky
    if 'error' in message.lower() or 'exception' in message.lower():
        # Ignorujeme běžné texty přepisů
        if not message.startswith("Zpracovávám text") and not message.startswith("[GROQ"):
            return True
            
    return False

def clean_path(path_str):
    # Odstraní bílé znaky a uvozovky, které přidává terminál při přetažení souboru
    return path_str.strip().strip("'").strip('"')

def main():
    print("=== Nástroj pro analýzu API chyb z LOGů do CSV ===")
    
    csv_input = input("Zadejte cestu k CSV souboru (např. C:/data/sim_study.csv): ")
    csv_path = clean_path(csv_input)
    
    log_paths_input = input("Zadejte cesty k LOG souborům (oddělené čárkou, nebo např. C:/logy/*.log): ")
    
    # Zpracování zadaných cest pro logy
    log_files = []
    # Rozdělení podle čárky a vyčištění každé cesty zvlášť
    for path in log_paths_input.split(','):
        path = clean_path(path)
        if not path:
            continue
            
        if '*' in path:
            log_files.extend(glob.glob(path))
        elif os.path.exists(path):
            log_files.append(path)
        else:
            print(f"Upozornění: Soubor {path} nebyl nalezen.")
            
    if not log_files:
        print("Chyba: Nebyly nalezeny žádné platné log soubory k analýze.")
        return

    # Načtení CSV
    try:
        df = pd.read_csv(csv_path, sep=';')
    except Exception as e:
        print(f"Kritická chyba při načítání CSV: {e}")
        return

    # Převod času na datetime objekt a seřazení chronologicky
    if 'Čas' not in df.columns:
        print("Chyba: CSV soubor neobsahuje sloupec 'Čas'.")
        return
        
    df['Čas_dt'] = pd.to_datetime(df['Čas'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    df = df.sort_values('Čas_dt').reset_index(drop=True)

    # Načtení Logů
    logs = []
    print(f"Načítám logy z {len(log_files)} souborů...")
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    timestamp, level, message = parse_log_line(line)
                    if timestamp:
                        logs.append({'time': timestamp, 'level': level, 'message': message})
        except Exception as e:
            print(f"Chyba při čtení logu {log_file}: {e}")

    logs_df = pd.DataFrame(logs)
    if not logs_df.empty:
        logs_df = logs_df.sort_values('time').reset_index(drop=True)

    # Vyhodnocování chybových intervalů
    error_counts = []
    error_descriptions = []

    print("Analyzuji časové intervaly a hledám chyby...")
    for i in range(len(df)):
        start_time = df.loc[i, 'Čas_dt']
        
        # Ošetření prázdných časů
        if pd.isna(start_time):
            error_counts.append(0)
            error_descriptions.append('')
            continue
            
        # Zjištění konce intervalu
        if i < len(df) - 1 and not pd.isna(df.loc[i+1, 'Čas_dt']):
            end_time = df.loc[i+1, 'Čas_dt']
        else:
            end_time = start_time + pd.Timedelta(minutes=1)

        # Filtrace logů spadajících do tohoto časového okna
        if not logs_df.empty:
            mask = (logs_df['time'] >= start_time) & (logs_df['time'] < end_time)
            interval_logs = logs_df[mask]
            
            # Hledání chyb v daném intervalu
            errors = []
            for _, row in interval_logs.iterrows():
                if is_api_error(row['level'], row['message']):
                    errors.append(row['message'])
            
            error_counts.append(len(errors))
            desc = " | ".join(errors)
            error_descriptions.append(desc)
        else:
            error_counts.append(0)
            error_descriptions.append('')

    # Přiřazení výsledků do nových sloupců CSV
    df['Počet chyb API'] = error_counts
    df['Popis chyb API'] = error_descriptions

    # Úklid pomocných sloupců
    df = df.drop(columns=['Čas_dt'])
    
    # Uložení do stejného adresáře jako vstupní soubor
    base_dir = os.path.dirname(os.path.abspath(csv_path))
    file_name = os.path.basename(csv_path)
    
    if file_name.endswith('.csv'):
        new_file_name = file_name.replace('.csv', '_analyzed.csv')
    else:
        new_file_name = file_name + '_analyzed.csv'
        
    output_path = os.path.join(base_dir, new_file_name)
    
    try:
        df.to_csv(output_path, sep=';', index=False, encoding='utf-8-sig')
        print(f"\nHotovo! Výsledek byl úspěšně uložen do stejného adresáře:\n{output_path}")
    except Exception as e:
        print(f"Chyba při ukládání souboru: {e}")

if __name__ == "__main__":
    main()