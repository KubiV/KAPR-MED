import sys
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                             QScrollArea, QTextEdit, QSplitter, QMessageBox)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import QUrl, Qt

# --- POMOCNÁ FUNKCE PRO FORMÁTOVÁNÍ ČASU ---
def format_timestamp(seconds):
    """Převede sekundy (float) na formát MM:SS"""
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    # Zobrazíme hodiny:minuty:sekundy (zaokrouhlené)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"

# --- SIMULACE AI PROCESORU ---
class AIProcessor:
    @staticmethod
    def process_text(text):
        print(f"--> AI ZPRACOVÁVÁ: '{text}'")
        # Zde můžeš napojit skutečné API
        return f"[AI]: {text}"

# --- WIDGET PRO JEDEN ŘÁDEK TITULKU ---
class SubtitleRow(QWidget):
    def __init__(self, data_item, player_reference, parent=None):
        super().__init__(parent)
        self.player = player_reference # Odkaz na přehrávač pro skákání v čase
        self.original_data = data_item # Uložíme si kompletní data (včetně tokenů atd.)
        
        # Načtení dat z Whisper JSONu (start/end jsou float sekundy)
        self.start_sec = data_item.get('start', 0.0)
        self.end_sec = data_item.get('end', 0.0)
        
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 5, 0, 5)
        
        # 1. Tlačítko pro skok v čase (Play ikona)
        self.btn_seek = QPushButton("▶")
        self.btn_seek.setFixedWidth(30)
        self.btn_seek.setToolTip(f"Skočit na čas {format_timestamp(self.start_sec)}")
        self.btn_seek.clicked.connect(self.seek_video)
        
        # 2. Časová značka (Label)
        time_str = f"{format_timestamp(self.start_sec)} - {format_timestamp(self.end_sec)}"
        self.lbl_time = QLabel(time_str)
        self.lbl_time.setFixedWidth(90)
        self.lbl_time.setStyleSheet("color: #555; font-size: 11px; font-weight: bold;")
        
        # 3. Editovatelný text
        self.txt_content = QTextEdit()
        # Whisper JSON má text často s mezerou na začátku, tu stripneme pro hezčí editaci
        initial_text = data_item.get('text', '').strip() 
        self.txt_content.setPlainText(initial_text)
        self.txt_content.setFixedHeight(50)
        
        # 4. Tlačítko pro AI
        self.btn_ai = QPushButton("AI")
        self.btn_ai.setFixedWidth(40)
        self.btn_ai.setStyleSheet("background-color: #e0e0e0;")
        self.btn_ai.clicked.connect(self.run_ai_single)
        
        self.layout.addWidget(self.btn_seek)
        self.layout.addWidget(self.lbl_time)
        self.layout.addWidget(self.txt_content)
        self.layout.addWidget(self.btn_ai)
        
        self.setLayout(self.layout)

    def seek_video(self):
        """Přesune video na začátek tohoto titulku"""
        # QMediaPlayer očekává milisekundy (int), v JSONu jsou sekundy (float)
        position_ms = int(self.start_sec * 1000)
        self.player.setPosition(position_ms)
        self.player.play()

    def run_ai_single(self):
        current_text = self.txt_content.toPlainText()
        result = AIProcessor.process_text(current_text)
        print(f"Výsledek: {result}")

    def get_updated_data(self):
        """Vrátí původní objekt s aktualizovaným textem"""
        # Do původních dat (kde jsou tokens, seek, atd.) vložíme nový text
        # Whisper texty často začínají mezerou, přidáme ji zpět pro konzistenci, pokud chceš
        updated_text = " " + self.txt_content.toPlainText().strip()
        self.original_data['text'] = updated_text
        return self.original_data

# --- HLAVNÍ OKNO ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Whisper Subtitle Editor")
        self.resize(1200, 800)
        
        self.subtitle_rows = [] 

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- VIDEO ČÁST ---
        video_container = QWidget()
        video_layout = QVBoxLayout(video_container)
        
        self.video_widget = QVideoWidget()
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)
        
        controls = QHBoxLayout()
        self.btn_open_video = QPushButton("Načíst Video")
        self.btn_open_video.clicked.connect(self.open_video)
        self.btn_play = QPushButton("Play/Pause")
        self.btn_play.clicked.connect(self.toggle_play)
        
        controls.addWidget(self.btn_open_video)
        controls.addWidget(self.btn_play)
        
        video_layout.addWidget(self.video_widget)
        video_layout.addLayout(controls)
        
        # --- TITULKY ČÁST ---
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        
        top_panel = QHBoxLayout()
        self.btn_load = QPushButton("📂 Načíst JSON")
        self.btn_load.clicked.connect(self.load_json)
        self.btn_save = QPushButton("💾 Uložit JSON")
        self.btn_save.clicked.connect(self.save_json)
        self.btn_ai_all = QPushButton("🤖 AI Vše")
        self.btn_ai_all.clicked.connect(self.process_all)
        
        top_panel.addWidget(self.btn_load)
        top_panel.addWidget(self.btn_save)
        top_panel.addWidget(self.btn_ai_all)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.scroll_content)
        
        right_layout.addLayout(top_panel)
        right_layout.addWidget(self.scroll)
        
        splitter.addWidget(video_container)
        splitter.addWidget(right_container)
        splitter.setSizes([700, 500])
        
        main_layout.addWidget(splitter)

    def open_video(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Vybrat Video")
        if fname:
            self.player.setSource(QUrl.fromLocalFile(fname))
            self.btn_play.setText("Play")

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def load_json(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Vybrat JSON", filter="JSON (*.json)")
        if not fname: return

        # Vyčistit staré
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.subtitle_rows = []

        try:
            with open(fname, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Pokud je JSON list (tvůj případ), projdeme ho
            if isinstance(data, list):
                for item in data:
                    # Předáváme 'self.player' pro možnost seekování
                    row = SubtitleRow(item, self.player)
                    self.scroll_layout.addWidget(row)
                    self.subtitle_rows.append(row)
            else:
                 # Pokud by to byl jiný formát (např. dict s klíčem 'segments')
                 segments = data.get('segments', [])
                 for item in segments:
                    row = SubtitleRow(item, self.player)
                    self.scroll_layout.addWidget(row)
                    self.subtitle_rows.append(row)
                
        except Exception as e:
            print(f"Chyba JSON: {e}")
            QMessageBox.critical(self, "Chyba", str(e))

    def save_json(self):
        if not self.subtitle_rows: return
        fname, _ = QFileDialog.getSaveFileName(self, "Uložit JSON", filter="JSON (*.json)")
        if not fname: return
            
        output_data = []
        for row in self.subtitle_rows:
            # Získáme kompletní data včetně upraveného textu
            output_data.append(row.get_updated_data())
            
        try:
            with open(fname, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            QMessageBox.information(self, "Hotovo", "Uloženo!")
        except Exception as e:
            QMessageBox.critical(self, "Chyba", str(e))

    def process_all(self):
        for row in self.subtitle_rows:
            row.run_ai_single()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())