import sys
import pandas as pd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                                 QHBoxLayout, QLabel, QTextEdit, QPushButton,
                                 QComboBox, QFormLayout, QMessageBox, QGroupBox)

class DataReviewApp(QMainWindow):
    def __init__(self, csv_file):
        super().__init__()
        self.csv_file = csv_file
        self.current_idx = 0
        
        # Názvy sloupců z CSV
        self.col_time = 'Čas'
        self.col_text1 = 'Přepsaný text'
        self.col_text2 = 'JSON Text'
        self.col_extracted = 'Extrahovaná data'
        self.col_eval = 'Vyhodnocení správně - ANO/NE'
        self.col_err = 'Typ chyby (když NE - typ 1 - kompletně chybí. 2 - chyba v položce, 3 - chyba v počtu)'
        self.col_manual = 'Manuální extrahovaná data'

        self.load_data()
        self.init_ui()
        self.load_row()

    def load_data(self):
        try:
            self.df = pd.read_csv(self.csv_file, sep=';', dtype=str).fillna('')
            # Vytvoření nového sloupce pro manuální data, pokud tam ještě není
            if self.col_manual not in self.df.columns:
                if self.col_extracted in self.df.columns:
                    self.df[self.col_manual] = self.df[self.col_extracted]
                else:
                    self.df[self.col_manual] = ""
        except FileNotFoundError:
            # Pokud soubor vůbec neexistuje, vytvoříme prázdný DataFrame se správnými sloupci
            cols = [self.col_time, self.col_text1, self.col_extracted, self.col_eval, 
                    self.col_err, self.col_text2, self.col_manual]
            self.df = pd.DataFrame(columns=cols)
        except Exception as e:
            print(f"Chyba při načítání CSV: {e}")
            sys.exit(1)

    def init_ui(self):
        self.setWindowTitle('Nástroj pro kontrolu a revizi dat')
        self.resize(1100, 800)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # --- Hlavička: Čas a Info ---
        header_layout = QHBoxLayout()
        self.lbl_progress = QLabel()
        self.lbl_time = QLabel()
        self.lbl_time.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(self.lbl_progress)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_time)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # --- Extrahovaná data ---
        self.lbl_extracted = QLabel()
        self.lbl_extracted.setStyleSheet("background-color: #f0f0f0; padding: 5px; border: 1px solid #ccc;")
        self.lbl_extracted.setWordWrap(True)
        main_layout.addWidget(QLabel("<b>Původní extrahovaná data:</b>"))
        main_layout.addWidget(self.lbl_extracted)

        # --- Porovnání textů (Dva sloupce - editovatelné) ---
        texts_layout = QHBoxLayout()

        # Levý sloupec (Přepsaný text)
        left_group = QGroupBox("Přepsaný text (Lze upravit)")
        left_layout = QVBoxLayout(left_group)
        self.ctx_up_left = QLabel()
        self.ctx_up_left.setStyleSheet("color: gray; font-style: italic;")
        self.ctx_up_left.setWordWrap(True)
        
        self.main_left = QTextEdit()
        self.main_left.setStyleSheet("font-size: 13px;")
        
        self.ctx_down_left = QLabel()
        self.ctx_down_left.setStyleSheet("color: gray; font-style: italic;")
        self.ctx_down_left.setWordWrap(True)

        left_layout.addWidget(self.ctx_up_left)
        left_layout.addWidget(self.main_left)
        left_layout.addWidget(self.ctx_down_left)
        texts_layout.addWidget(left_group)

        # Pravý sloupec (JSON Text)
        right_group = QGroupBox("JSON Text (Lze upravit)")
        right_layout = QVBoxLayout(right_group)
        self.ctx_up_right = QLabel()
        self.ctx_up_right.setStyleSheet("color: gray; font-style: italic;")
        self.ctx_up_right.setWordWrap(True)
        
        self.main_right = QTextEdit()
        self.main_right.setStyleSheet("font-size: 13px;")
        
        self.ctx_down_right = QLabel()
        self.ctx_down_right.setStyleSheet("color: gray; font-style: italic;")
        self.ctx_down_right.setWordWrap(True)

        right_layout.addWidget(self.ctx_up_right)
        right_layout.addWidget(self.main_right)
        right_layout.addWidget(self.ctx_down_right)
        texts_layout.addWidget(right_group)

        main_layout.addLayout(texts_layout)

        # --- Vstupní formulář ---
        form_group = QGroupBox("Manuální hodnocení a korekce")
        form_layout = QFormLayout(form_group)

        self.combo_eval = QComboBox()
        self.combo_eval.addItems(["", "ANO", "NE"])
        
        self.combo_err = QComboBox()
        self.combo_err.addItems(["", "1", "2", "3", "4", "5"])
        
        # Rozšířený popisek s vysvětlivkami chyb
        lbl_err_desc = QLabel(
            "<i>1 = kompletně chybí &nbsp;&nbsp;|&nbsp;&nbsp; "
            "2 = chyba v položce &nbsp;&nbsp;|&nbsp;&nbsp; "
            "3 = v počtu nebo v hodnotě &nbsp;&nbsp;|&nbsp;&nbsp; "
            "4 = chyba v přepisu &nbsp;&nbsp;|&nbsp;&nbsp; "
            "5 = v přepisu chybí položka</i>"
        )
        lbl_err_desc.setStyleSheet("color: #444; font-size: 11px;")
        
        self.edit_manual = QTextEdit()
        self.edit_manual.setMaximumHeight(80)

        # Upravený text u ANO/NE
        form_layout.addRow("Vyhodnocení správně (ANO je-li popis alespoň částečně správně):", self.combo_eval)
        form_layout.addRow("Typ chyby (1-5):", self.combo_err)
        form_layout.addRow("", lbl_err_desc)
        form_layout.addRow("Manuální extrahovaná data:", self.edit_manual)
        
        main_layout.addWidget(form_group)

        # --- Tlačítka ---
        btn_layout = QHBoxLayout()
        self.btn_prev = QPushButton("<< Předchozí")
        self.btn_prev.clicked.connect(self.prev_row)
        
        self.btn_next = QPushButton("Další >>")
        self.btn_next.clicked.connect(self.next_row)
        
        # Upravené tlačítko pro vmezeření řádku
        self.btn_insert_row = QPushButton("+ Vložit řádek za aktuální")
        self.btn_insert_row.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.btn_insert_row.clicked.connect(self.insert_new_row)

        self.btn_save = QPushButton("Průběžně uložit do CSV")
        self.btn_save.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_save.clicked.connect(self.save_csv)

        btn_layout.addWidget(self.btn_prev)
        btn_layout.addWidget(self.btn_next)
        btn_layout.addSpacing(20)
        btn_layout.addWidget(self.btn_insert_row)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        
        main_layout.addLayout(btn_layout)

    def load_row(self):
        if len(self.df) == 0:
            self.lbl_progress.setText("Žádná data")
            return

        row = self.df.iloc[self.current_idx]
        
        # Info
        self.lbl_progress.setText(f"Řádek: {self.current_idx + 1} / {len(self.df)}")
        self.lbl_time.setText(f"Čas: {row.get(self.col_time, '')}")
        self.lbl_extracted.setText(str(row.get(self.col_extracted, '')))

        # Hlavní texty (lze editovat)
        self.main_left.setPlainText(str(row.get(self.col_text1, '')))
        self.main_right.setPlainText(str(row.get(self.col_text2, '')))

        # Kontext nahoru
        if self.current_idx > 0:
            row_up = self.df.iloc[self.current_idx - 1]
            self.ctx_up_left.setText(str(row_up.get(self.col_text1, '')))
            self.ctx_up_right.setText(str(row_up.get(self.col_text2, '')))
        else:
            self.ctx_up_left.setText("")
            self.ctx_up_right.setText("")

        # Kontext dolů
        if self.current_idx < len(self.df) - 1:
            row_down = self.df.iloc[self.current_idx + 1]
            self.ctx_down_left.setText(str(row_down.get(self.col_text1, '')))
            self.ctx_down_right.setText(str(row_down.get(self.col_text2, '')))
        else:
            self.ctx_down_left.setText("")
            self.ctx_down_right.setText("")

        # Načtení formuláře
        self.combo_eval.setCurrentText(str(row.get(self.col_eval, '')))
        self.combo_err.setCurrentText(str(row.get(self.col_err, '')))
        self.edit_manual.setPlainText(str(row.get(self.col_manual, '')))

        # Tlačítka states
        self.btn_prev.setEnabled(self.current_idx > 0)
        self.btn_next.setEnabled(self.current_idx < len(self.df) - 1)

    def save_current_inputs(self):
        if len(self.df) == 0:
            return
            
        # Uložení z GUI zpět do DataFrame
        self.df.at[self.current_idx, self.col_text1] = self.main_left.toPlainText()
        self.df.at[self.current_idx, self.col_text2] = self.main_right.toPlainText()
        self.df.at[self.current_idx, self.col_eval] = self.combo_eval.currentText()
        self.df.at[self.current_idx, self.col_err] = self.combo_err.currentText()
        self.df.at[self.current_idx, self.col_manual] = self.edit_manual.toPlainText()

    def prev_row(self):
        self.save_current_inputs()
        if self.current_idx > 0:
            self.current_idx -= 1
            self.load_row()

    def next_row(self):
        self.save_current_inputs()
        if self.current_idx < len(self.df) - 1:
            self.current_idx += 1
            self.load_row()

    def insert_new_row(self):
        self.save_current_inputs()
        
        # Vytvoříme prázdný řádek se všemi sloupci
        new_row_data = {col: '' for col in self.df.columns}
        new_row_df = pd.DataFrame([new_row_data])
        
        # Rozdělení DataFrame a vmezeření nového řádku ZA aktuální pozici
        part1 = self.df.iloc[:self.current_idx + 1]
        part2 = self.df.iloc[self.current_idx + 1:]
        
        self.df = pd.concat([part1, new_row_df, part2], ignore_index=True)
        
        # Posuneme index na ten nově vmezeřený řádek (který je hned za tím předchozím)
        self.current_idx += 1
        self.load_row()

    def save_csv(self):
        self.save_current_inputs()
        try:
            # Ukládáme rovnou do původního souboru
            self.df.to_csv(self.csv_file, sep=';', index=False, encoding='utf-8')
            QMessageBox.information(self, "Uloženo", f"Data byla úspěšně uložena do souboru:\n{self.csv_file}\n(Můžeš pokračovat v práci.)")
        except Exception as e:
            QMessageBox.critical(self, "Chyba", f"Nepodařilo se uložit soubor:\n{e}\n\nZkontroluj, zda soubor není otevřený v jiném programu (např. v Excelu).")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Nastavení jména souboru (soubor se bude načítat i přepisovat)
    csv_filename = "combined.csv" 
    
    window = DataReviewApp(csv_filename)
    window.show()
    sys.exit(app.exec())