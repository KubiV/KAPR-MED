import soundfile as sf
import numpy as np
import os

# --- Nastavení generátoru ---
TON_FREKVENCE = 440   # Hz (např. 1000 Hz pro pískání)
HLASITOST = 0.1       # 0.0 až 1.0 (šum je hlasitý, doporučuji málo!)

def generuj_vypln_float(typ, pocet_vzorku, kanaly, samplerate):
    """
    Generuje data ve formátu float32 (-1.0 až 1.0), což soundfile preferuje.
    """
    if typ == 'ticho':
        if kanaly > 1:
            return np.zeros((pocet_vzorku, kanaly), dtype=np.float32)
        return np.zeros(pocet_vzorku, dtype=np.float32)

    elif typ == 'sum':
        # Bílý šum
        data = np.random.uniform(-HLASITOST, HLASITOST, size=(pocet_vzorku, kanaly))
        if kanaly == 1:
            data = data.flatten()
        return data.astype(np.float32)

    elif typ == 'ton':
        # Sinusoida
        t = np.arange(pocet_vzorku) / samplerate
        # Vzorec vlny
        wave = np.sin(2 * np.pi * TON_FREKVENCE * t) * HLASITOST
        
        if kanaly > 1:
            # Rozkopírování pro stereo/více kanálů
            return np.tile(wave[:, np.newaxis], (1, kanaly)).astype(np.float32)
        return wave.astype(np.float32)
    
    return None

def split_wav_to_flac_advanced():
    print("--- Ultimátní rozdělovač (WAV -> FLAC s generátorem) ---")
    
    # 1. Vstup
    input_path = input("Zadejte cestu k WAV souboru: ").strip().replace('"', '').replace("'", "")
    
    if not os.path.isfile(input_path):
        print("Soubor nenalezen.")
        return

    # 2. Volba výplně
    print("\nVyberte výplň prázdné části:")
    print("1 - Ticho (Velikost souboru: MINIMÁLNÍ)")
    print(f"2 - Tón {TON_FREKVENCE}Hz (Velikost souboru: MALÁ)")
    print(f"3 - Šum (Velikost souboru: VELKÁ - šum nejde komprimovat!)")
    
    volba = input("Volba (1/2/3): ").strip()
    typ_vyplne = 'ticho'
    if volba == '2': typ_vyplne = 'ton'
    if volba == '3': typ_vyplne = 'sum'

    try:
        directory = os.path.dirname(os.path.abspath(input_path))
        filename = os.path.basename(input_path)
        name_only, _ = os.path.splitext(filename)

        print("Načítám audio...")
        # Soundfile načte data rovnou jako float pole (-1.0 až 1.0)
        original_data, samplerate = sf.read(input_path)
        
        # Zjištění počtu kanálů (mono = 1, stereo = 2, atd.)
        # Pokud je shape např. (1000,), je to mono. Pokud (1000, 2), je to stereo.
        if len(original_data.shape) > 1:
            channels = original_data.shape[1]
        else:
            channels = 1

        total_frames = len(original_data)
        midpoint = total_frames // 2

        # Rozdělení originálu
        part1_orig = original_data[:midpoint]
        part2_orig = original_data[midpoint:]

        print(f"Generuji výplň typu: {typ_vyplne.upper()}...")
        
        # Vygenerování "falešných" dat
        fill_part2 = generuj_vypln_float(typ_vyplne, len(part2_orig), channels, samplerate)
        fill_part1 = generuj_vypln_float(typ_vyplne, len(part1_orig), channels, samplerate)

        # --- Spojování a ukládání ---
        
        # 1. Část (Originál -> Výplň)
        out1_data = np.concatenate((part1_orig, fill_part2))
        out1_path = os.path.join(directory, f"{name_only}_part1_{typ_vyplne}.flac")
        print(f"Ukládám FLAC: {os.path.basename(out1_path)}")
        sf.write(out1_path, out1_data, samplerate)

        # 2. Část (Výplň -> Originál)
        out2_data = np.concatenate((fill_part1, part2_orig))
        out2_path = os.path.join(directory, f"{name_only}_part2_{typ_vyplne}.flac")
        print(f"Ukládám FLAC: {os.path.basename(out2_path)}")
        sf.write(out2_path, out2_data, samplerate)

        print("\nHotovo!")
        if typ_vyplne == 'sum':
            print("INFO: Zvolil jste šum. Soubory budou velké, protože šum je náhodná informace.")
        else:
            print("INFO: Zvolil jste ticho/tón. Soubory by měly být výrazně menší než originál.")

    except Exception as e:
        print(f"Chyba: {e}")

if __name__ == "__main__":
    split_wav_to_flac_advanced()
    input("\nStiskněte Enter pro ukončení...")