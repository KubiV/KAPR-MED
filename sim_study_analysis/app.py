import sys
import json
import os
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                             QScrollArea, QTextEdit, QSplitter, QMessageBox, 
                             QSlider, QComboBox, QProgressBar)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import QUrl, Qt, QTimer, QThread, pyqtSignal

# --- IMPORT AI LOGIKY ---
# Předpokládá existenci souboru ai_logic.py ve stejné složce
try:
    import ai_logic
except ImportError:
    # Fallback pro případ, že ai_logic chybí (aby program nespadl hned)
    print("VAROVÁNÍ: Soubor 'ai_logic.py' nebyl nalezen. AI funkce nebudou fungovat.")
    class MockAIService:
        @staticmethod
        def query_llm(text): return {"polozky": {"error": "Chybí ai_logic.py"}}
    class MockSessionManager:
        def reset_tables(self): pass
        def process_data_into_tables(self, d, t): pass
        def save_session(self): return ".", ["error.csv"]
    ai_logic = type('obj', (object,), {'AIService': MockAIService, 'SessionManager': MockSessionManager})

def format_timestamp(ms):
    """Převede milisekundy na formát HH:MM:SS"""
    s = ms // 1000
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"

# --- WORKER PRO AI (Aby nezamrzalo okno) ---
class AIWorker(QThread):
    finished = pyqtSignal(object, str, object) # row_widget, result_text, json_data

    def __init__(self, text, row_widget):
        super().__init__()
        self.text = text
        self.row_widget = row_widget

    def run(self):
        try:
            # Volání funkce ze separátního souboru
            result_json = ai_logic.AIService.query_llm(self.text)
            
            if result_json:
                pretty_text = json.dumps(result_json.get('polozky', {}), ensure_ascii=False, indent=2)
                self.finished.emit(self.row_widget, pretty_text, result_json)
            else:
                self.finished.emit(self.row_widget, "Žádná data / Chyba", {})
        except Exception as e:
            self.finished.emit(self.row_widget, f"Error: {e}", {})

class SubtitleRow(QWidget):
    def __init__(self, data_item, player_reference, delete_callback, ai_callback, parent=None):
        super().__init__(parent)
        self.player = player_reference
        self.original_data = data_item
        self.delete_callback = delete_callback
        self.ai_callback = ai_callback 
        
        self.start_sec = data_item.get('start', 0.0)
        self.end_sec = data_item.get('end', self.start_sec + 2.0)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.is_highlighted = False
        
        self.analysis_json = data_item.get('ai_analysis', {}) 
        
        self.init_ui()
        self.update_style()

    def init_ui(self):
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(5, 5, 5, 5)
        
        self.btn_seek = QPushButton("▶")
        self.btn_seek.setFixedWidth(30)
        self.btn_seek.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_seek.clicked.connect(self.seek_video)
        
        time_str = format_timestamp(self.start_sec * 1000)
        self.lbl_time = QLabel(time_str)
        self.lbl_time.setFixedWidth(65)
        self.lbl_time.setStyleSheet("font-family: monospace; font-weight: bold; color: #000000;")
        
        self.txt_content = QTextEdit()
        self.txt_content.setPlainText(self.original_data.get('text', '').strip())
        self.txt_content.setFixedHeight(60)
        self.txt_content.setStyleSheet("background-color: #ffffff; color: #000000; border: 1px solid #ccc; border-radius: 4px;")
        
        # --- POLE PRO AI VÝSTUP ---
        self.txt_ai_result = QTextEdit()
        self.txt_ai_result.setPlaceholderText("AI Analýza...")
        if self.analysis_json:
             self.txt_ai_result.setPlainText(json.dumps(self.analysis_json.get('polozky', {}), ensure_ascii=False, indent=2))
        
        self.txt_ai_result.setFixedHeight(60)
        self.txt_ai_result.setStyleSheet("background-color: #e3f2fd; color: #0d47a1; border: 1px solid #90caf9; border-radius: 4px; font-size: 11px;")
        
        self.btn_ai = QPushButton("AI")
        self.btn_ai.setFixedWidth(35)
        self.btn_ai.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.btn_ai.clicked.connect(self.run_ai_single)

        self.btn_del = QPushButton("✕")
        self.btn_del.setFixedWidth(25)
        self.btn_del.setStyleSheet("QPushButton { color: red; font-weight: bold; border: none; } QPushButton:hover { background-color: #ffcccc; border-radius: 3px; }")
        self.btn_del.clicked.connect(lambda: self.delete_callback(self))
        
        self.layout.addWidget(self.btn_seek)
        self.layout.addWidget(self.lbl_time)
        self.layout.addWidget(self.txt_content, stretch=2)   
        self.layout.addWidget(self.txt_ai_result, stretch=1) 
        self.layout.addWidget(self.btn_ai)
        self.layout.addWidget(self.btn_del)
        self.setLayout(self.layout)

    def set_highlight(self, active):
        if self.is_highlighted == active: return 
        self.is_highlighted = active
        self.update_style()

    def update_style(self):
        if self.is_highlighted:
            self.setStyleSheet("SubtitleRow { background-color: #fffacd; border: 2px solid #ffd700; border-radius: 6px; } QLabel { color: black; }")
        else:
            self.setStyleSheet("SubtitleRow { background-color: #f9f9f9; border-bottom: 1px solid #e0e0e0; border-radius: 4px; } QLabel { color: black; }")

    def seek_video(self):
        self.player.setPosition(int(self.start_sec * 1000))
        self.player.play()

    def run_ai_single(self):
        text_to_process = self.txt_content.toPlainText()
        self.txt_ai_result.setPlainText("Pracuji...")
        self.ai_callback(self, text_to_process)

    def update_ai_result(self, text, json_data):
        self.txt_ai_result.setPlainText(text)
        self.analysis_json = json_data
        print(f"AI Hotovo pro čas {format_timestamp(self.start_sec*1000)}")

    def get_updated_data(self):
        self.original_data['text'] = " " + self.txt_content.toPlainText().strip()
        self.original_data['start'] = self.start_sec
        self.original_data['end'] = self.end_sec
        self.original_data['ai_analysis'] = self.analysis_json 
        return self.original_data

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Whisper Editor & AI Medical Analyzer (Merged Ultimate)")
        self.resize(1400, 850)
        
        self.subtitle_rows = []
        self.video_start_time = datetime.now()
        self.last_active_row = None
        
        # Inicializace Session Manageru
        self.session_manager = ai_logic.SessionManager()
        
        self.init_ui()
        
        self.timer = QTimer()
        self.timer.setInterval(100) 
        self.timer.timeout.connect(self.update_ui_state)
        self.timer.start()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_widget.setStyleSheet("background-color: #f0f0f0; color: #000000;")
        
        main_layout = QVBoxLayout(main_widget)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- VIDEO PANEL (Levá strana) ---
        video_container = QWidget()
        video_layout = QVBoxLayout(video_container)
        
        self.video_widget = QVideoWidget()
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)
        
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.sliderMoved.connect(self.set_video_position)
        self.slider.sliderPressed.connect(lambda: self.player.pause())
        
        # Ovládací prvky videa (Play, Seek, Speed)
        controls = QHBoxLayout()
        
        self.btn_play = QPushButton("Play/Pause")
        self.btn_play.clicked.connect(self.toggle_play)
        
        # -- Obnovené funkce: Seek -1s/+1s --
        self.btn_back = QPushButton("-1s")
        self.btn_back.clicked.connect(lambda: self.seek_relative(-1000))
        self.btn_fwd = QPushButton("+1s")
        self.btn_fwd.clicked.connect(lambda: self.seek_relative(1000))
        
        # -- Obnovená funkce: Rychlost --
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.5x", "1.0x", "1.25x", "1.5x", "2.0x"])
        self.speed_combo.setCurrentIndex(1)
        self.speed_combo.currentIndexChanged.connect(self.change_speed)
        
        self.lbl_current_time = QLabel("00:00:00")
        
        controls.addWidget(self.btn_play)
        controls.addWidget(self.btn_back)
        controls.addWidget(self.btn_fwd)
        controls.addWidget(QLabel("Rychlost:"))
        controls.addWidget(self.speed_combo)
        controls.addStretch()
        controls.addWidget(self.lbl_current_time)

        video_layout.addWidget(self.video_widget, stretch=5)
        video_layout.addWidget(self.slider)
        video_layout.addLayout(controls)
        
        # --- TIMELINE PANEL (Pravá strana) ---
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        
        top_menu = QHBoxLayout()
        btn_open_v = QPushButton("🎥 Video")
        btn_open_v.clicked.connect(self.open_video)
        btn_load_j = QPushButton("📂 JSON")
        btn_load_j.clicked.connect(self.load_json)
        btn_save_j = QPushButton("💾 Uložit Projekt")
        btn_save_j.clicked.connect(self.save_json)
        
        top_menu.addWidget(btn_open_v)
        top_menu.addWidget(btn_load_j)
        top_menu.addWidget(btn_save_j)

        subtitle_actions = QHBoxLayout()
        self.btn_autoscroll = QPushButton("⬇ Auto-Scroll: ZAP")
        self.btn_autoscroll.setCheckable(True)
        self.btn_autoscroll.setChecked(True)
        self.btn_autoscroll.clicked.connect(self.toggle_autoscroll_label)

        self.btn_add_sub = QPushButton("+ Přidat titulek")
        self.btn_add_sub.clicked.connect(self.add_subtitle_at_current)
        
        self.btn_ai_all = QPushButton("🧠 AI Vše + Uložit CSV")
        self.btn_ai_all.setStyleSheet("background-color: #673AB7; color: white; font-weight: bold;")
        self.btn_ai_all.clicked.connect(self.process_all_and_save)
        
        subtitle_actions.addWidget(self.btn_autoscroll)
        subtitle_actions.addWidget(self.btn_add_sub)
        subtitle_actions.addWidget(self.btn_ai_all)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { background-color: #ffffff; border: none; }")
        
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_layout.setSpacing(5)
        self.scroll.setWidget(self.scroll_content)
        
        right_layout.addLayout(top_menu)
        right_layout.addLayout(subtitle_actions)
        right_layout.addWidget(self.scroll)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        right_layout.addWidget(self.progress_bar)
        
        splitter.addWidget(video_container)
        splitter.addWidget(right_container)
        splitter.setSizes([600, 800])
        main_layout.addWidget(splitter)

    # --- OBSLUHA AI ---

    def handle_single_ai_request(self, row_widget, text):
        """Spustí thread pro analýzu jednoho řádku"""
        self.worker = AIWorker(text, row_widget)
        self.worker.finished.connect(self.on_single_ai_finished)
        self.worker.start()

    def on_single_ai_finished(self, row_widget, text, json_data):
        row_widget.update_ai_result(text, json_data)

    def process_all_and_save(self):
        """Proces pro dávkové zpracování"""
        if not self.subtitle_rows:
            QMessageBox.warning(self, "Chyba", "Žádné titulky ke zpracování.")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(self.subtitle_rows))
        self.progress_bar.setValue(0)
        self.btn_ai_all.setEnabled(False)
        
        # Resetovat tabulky v session manageru před novým průchodem
        self.session_manager.reset_tables()
        
        # Spustíme rekurzivní zpracování
        self.process_next_row(0)

    def process_next_row(self, index):
        if index >= len(self.subtitle_rows):
            self.finalize_processing()
            return

        row = self.subtitle_rows[index]
        text = row.txt_content.toPlainText()
        
        self.progress_bar.setValue(index + 1)
        
        # Worker pro daný řádek
        self.worker = AIWorker(text, row)
        self.worker.finished.connect(lambda r, t, j: self.on_row_processed(r, t, j, index))
        self.worker.start()

    def on_row_processed(self, row_widget, text, json_data, index):
        # 1. Update GUI prvku
        row_widget.update_ai_result(text, json_data)
        
        # 2. Předání dat do SessionManageru (pro CSV)
        if json_data:
            timestamp = format_timestamp(row_widget.start_sec * 1000)
            self.session_manager.process_data_into_tables(json_data, timestamp)

        # 3. Další řádek
        self.process_next_row(index + 1)

    def finalize_processing(self):
        self.progress_bar.setVisible(False)
        self.btn_ai_all.setEnabled(True)
        
        try:
            # Uložení CSV přes manager
            folder, files = self.session_manager.save_session()
            files_str = "\n".join(files)
            QMessageBox.information(self, "Hotovo", f"Analýza dokončena.\n\nUloženo do:\n{folder}\n\nSoubory:\n{files_str}")
        except Exception as e:
            QMessageBox.critical(self, "Chyba při ukládání", str(e))

    # --- STANDARDNÍ METODY (Sloučeno) ---
    def toggle_autoscroll_label(self):
        if self.btn_autoscroll.isChecked():
            self.btn_autoscroll.setText("⬇ Auto-Scroll: ZAP")
        else:
            self.btn_autoscroll.setText("⬇ Auto-Scroll: VYP")

    def update_ui_state(self):
        if self.player.duration() > 0:
            pos = self.player.position()
            current_sec = pos / 1000.0
            dur = self.player.duration()
            
            if not self.slider.isSliderDown():
                self.slider.setMaximum(dur)
                self.slider.setValue(pos)
            self.lbl_current_time.setText(format_timestamp(pos))
            self.highlight_subtitles(current_sec)

    def highlight_subtitles(self, current_sec):
        active_row = None
        for row in self.subtitle_rows:
            # Logika z prvního skriptu (lepší pro čtení)
            if row.start_sec <= current_sec:
                active_row = row
            else:
                break
        
        for row in self.subtitle_rows:
            # Použijeme barvení, ale zároveň zkontrolujeme, jestli sedí v autoscrollu
            row.set_highlight(row == active_row)

        if active_row and active_row != self.last_active_row:
            if self.btn_autoscroll.isChecked():
                self.scroll.verticalScrollBar().setValue(active_row.y())
            self.last_active_row = active_row

    def open_video(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Vybrat Video")
        if fname:
            self.player.setSource(QUrl.fromLocalFile(fname))
            # Reset rychlosti při načtení nového videa
            self.player.setPlaybackRate(1.0)
            self.speed_combo.setCurrentIndex(1)
            
            # Načtení reálného času (z druhého skriptu)
            try:
                self.video_start_time = datetime.fromtimestamp(os.path.getmtime(fname))
            except:
                self.video_start_time = datetime.now()

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def set_video_position(self, position):
        self.player.setPosition(position)
        self.lbl_current_time.setText(format_timestamp(position))
        self.highlight_subtitles(position / 1000.0)
    
    # -- Obnovené metody pro ovládání --
    def seek_relative(self, ms):
        self.player.setPosition(self.player.position() + ms)

    def change_speed(self):
        speed_txt = self.speed_combo.currentText().replace('x', '')
        try:
            speed = float(speed_txt)
            self.player.setPlaybackRate(speed)
        except ValueError:
            pass

    def add_subtitle_at_current(self):
        curr_ms = self.player.position()
        curr_sec = curr_ms / 1000.0
        new_item = { "start": curr_sec, "end": curr_sec + 2.0, "text": "Nový záznam" }
        row = SubtitleRow(new_item, self.player, self.delete_row, self.handle_single_ai_request)
        
        insert_idx = len(self.subtitle_rows)
        for i, r in enumerate(self.subtitle_rows):
            if r.start_sec > new_item['start']:
                insert_idx = i
                break
        
        self.scroll_layout.insertWidget(insert_idx, row)
        self.subtitle_rows.insert(insert_idx, row)
        self.subtitle_rows.sort(key=lambda x: x.start_sec)

    def delete_row(self, row_widget):
        if row_widget in self.subtitle_rows:
            self.subtitle_rows.remove(row_widget)
        row_widget.setParent(None)
        row_widget.deleteLater()

    def load_json(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Vybrat JSON", filter="JSON (*.json)")
        if not fname: return
        
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.subtitle_rows = []

        try:
            with open(fname, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            segments = data if isinstance(data, list) else data.get('segments', [])
            segments.sort(key=lambda x: x.get('start', 0))

            for item in segments:
                # Zde musíme předat i callback pro AI
                row = SubtitleRow(item, self.player, self.delete_row, self.handle_single_ai_request)
                self.scroll_layout.addWidget(row)
                self.subtitle_rows.append(row)
        except Exception as e:
            QMessageBox.critical(self, "Chyba", f"Nepodařilo se načíst JSON: {e}")

    def save_json(self):
        fname, _ = QFileDialog.getSaveFileName(self, "Uložit JSON", filter="JSON (*.json)")
        if not fname: return
        
        output = []
        for row in self.subtitle_rows:
            data = row.get_updated_data()
            
            # -- Obnovená logika: výpočet reálného času (exact_world_time) --
            try:
                offset = timedelta(seconds=data['start'])
                world_time = self.video_start_time + offset
                data['exact_world_time'] = world_time.strftime("%Y-%m-%d %H:%M:%S.%f")
            except Exception:
                data['exact_world_time'] = "N/A"
            
            output.append(data)

        try:
            with open(fname, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            QMessageBox.information(self, "Uloženo", "Soubor byl uložen (včetně AI dat a časových značek).")
        except Exception as e:
            QMessageBox.critical(self, "Chyba", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion") 
    window = MainWindow()
    window.show()
    sys.exit(app.exec())