import sys
import json
import os
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                             QScrollArea, QTextEdit, QSplitter, QMessageBox, 
                             QSlider, QComboBox)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import QUrl, Qt, QTimer

def format_timestamp(ms):
    """Převede milisekundy na formát HH:MM:SS"""
    s = ms // 1000
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"

class AIProcessor:
    @staticmethod
    def process_text(text):
        return f"[AI]: {text}"

class SubtitleRow(QWidget):
    def __init__(self, data_item, player_reference, delete_callback, parent=None):
        super().__init__(parent)
        self.player = player_reference
        self.original_data = data_item
        self.delete_callback = delete_callback
        
        # Whisper data (v sekundách)
        self.start_sec = data_item.get('start', 0.0)
        self.end_sec = data_item.get('end', self.start_sec + 2.0)
        
        # Aby QWidget podporoval stylování pozadí
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.is_highlighted = False
        
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
        # Vynucení černé barvy textu pro Dark Mode kompatibilitu
        self.lbl_time.setStyleSheet("font-family: monospace; font-weight: bold; color: #000000;")
        
        self.txt_content = QTextEdit()
        self.txt_content.setPlainText(self.original_data.get('text', '').strip())
        self.txt_content.setFixedHeight(50)
        # Vynucení bílého pozadí a černého textu (natvrdo)
        self.txt_content.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff; 
                color: #000000;
                border: 1px solid #ccc; 
                border-radius: 4px;
            }
        """)
        
        self.btn_ai = QPushButton("AI")
        self.btn_ai.setFixedWidth(35)
        self.btn_ai.clicked.connect(self.run_ai_single)

        self.btn_del = QPushButton("✕")
        self.btn_del.setFixedWidth(25)
        self.btn_del.setStyleSheet("QPushButton { color: red; font-weight: bold; border: none; } QPushButton:hover { background-color: #ffcccc; border-radius: 3px; }")
        self.btn_del.clicked.connect(lambda: self.delete_callback(self))
        
        self.layout.addWidget(self.btn_seek)
        self.layout.addWidget(self.lbl_time)
        self.layout.addWidget(self.txt_content)
        self.layout.addWidget(self.btn_ai)
        self.layout.addWidget(self.btn_del)
        self.setLayout(self.layout)

    def set_highlight(self, active):
        if self.is_highlighted == active:
            return 
        self.is_highlighted = active
        self.update_style()

    def update_style(self):
        if self.is_highlighted:
            # Aktivní: žluté podbarvení, černý text (vynuceno)
            self.setStyleSheet("""
                SubtitleRow {
                    background-color: #fffacd; 
                    border: 2px solid #ffd700;
                    border-radius: 6px;
                }
                QLabel { color: black; }
            """)
        else:
            # Neaktivní: šedobílé pozadí
            self.setStyleSheet("""
                SubtitleRow {
                    background-color: #f9f9f9;
                    border-bottom: 1px solid #e0e0e0;
                    border-radius: 4px;
                }
                QLabel { color: black; }
            """)

    def seek_video(self):
        self.player.setPosition(int(self.start_sec * 1000))
        self.player.play()

    def run_ai_single(self):
        res = AIProcessor.process_text(self.txt_content.toPlainText())
        self.txt_content.setPlainText(res)

    def get_updated_data(self):
        self.original_data['text'] = " " + self.txt_content.toPlainText().strip()
        self.original_data['start'] = self.start_sec
        self.original_data['end'] = self.end_sec
        return self.original_data

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Whisper Editor & Timeline (+ AutoScroll)")
        self.resize(1300, 850)
        
        self.subtitle_rows = []
        self.video_start_time = datetime.now()
        
        # Proměnná pro sledování posledního aktivního titulku (pro scrollování)
        self.last_active_row = None
        
        self.init_ui()
        
        self.timer = QTimer()
        self.timer.setInterval(100) 
        self.timer.timeout.connect(self.update_ui_state)
        self.timer.start()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        # Nastavíme pozadí hlavního okna na neutrální šedou, aby to nebilo do očí v dark mode
        main_widget.setStyleSheet("background-color: #f0f0f0; color: #000000;")
        
        main_layout = QVBoxLayout(main_widget)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- LEVÁ STRANA ---
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
        
        controls = QHBoxLayout()
        self.btn_play = QPushButton("Play/Pause")
        self.btn_play.clicked.connect(self.toggle_play)
        
        self.btn_back = QPushButton("-1s")
        self.btn_back.clicked.connect(lambda: self.seek_relative(-1000))
        self.btn_fwd = QPushButton("+1s")
        self.btn_fwd.clicked.connect(lambda: self.seek_relative(1000))
        
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
        
        # --- PRAVÁ STRANA ---
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        
        top_menu = QHBoxLayout()
        btn_open_v = QPushButton("🎥 Video")
        btn_open_v.clicked.connect(self.open_video)
        btn_load_j = QPushButton("📂 JSON")
        btn_load_j.clicked.connect(self.load_json)
        btn_save_j = QPushButton("💾 Uložit")
        btn_save_j.clicked.connect(self.save_json)
        
        top_menu.addWidget(btn_open_v)
        top_menu.addWidget(btn_load_j)
        top_menu.addWidget(btn_save_j)

        subtitle_actions = QHBoxLayout()
        
        # Tlačítko pro Auto-Scroll
        self.btn_autoscroll = QPushButton("⬇ Auto-Scroll: ZAP")
        self.btn_autoscroll.setCheckable(True)
        self.btn_autoscroll.setChecked(True) # Defaultně zapnuto
        self.btn_autoscroll.setStyleSheet("""
            QPushButton:checked { background-color: #4CAF50; color: white; }
            QPushButton:unchecked { background-color: #e0e0e0; color: black; }
        """)
        self.btn_autoscroll.clicked.connect(self.toggle_autoscroll_label)

        self.btn_add_sub = QPushButton("+ Přidat titulek")
        self.btn_add_sub.setStyleSheet("background-color: #d4edda; color: black;")
        self.btn_add_sub.clicked.connect(self.add_subtitle_at_current)
        
        self.btn_ai_all = QPushButton("🤖 AI Vše")
        self.btn_ai_all.clicked.connect(self.process_all)
        
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
        
        splitter.addWidget(video_container)
        splitter.addWidget(right_container)
        splitter.setSizes([600, 700])
        main_layout.addWidget(splitter)

    # --- LOGIKA ---

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
        """
        Logic: Najde poslední titulek, který začal před aktuálním časem.
        Ten bude aktivní, dokud nezačne další (nebo video neskončí).
        """
        active_row = None
        
        # 1. Najít kandidáta (poslední řádek, kde start <= current)
        # Předpokládáme, že self.subtitle_rows je seřazené podle času
        for row in self.subtitle_rows:
            if row.start_sec <= current_sec:
                active_row = row
            else:
                # Jakmile narazíme na titulek, co začíná v budoucnu, končíme
                break
        
        # 2. Nastavit highlight
        for row in self.subtitle_rows:
            is_active = (row == active_row)
            row.set_highlight(is_active)

        # 3. Auto-Scroll logic
        # Scrolujeme pouze pokud:
        # a) Máme aktivní řádek
        # b) Aktivní řádek se změnil oproti minule (abychom uživatele neblokovali při manuálním posunu)
        # c) Funkce je zapnutá
        if active_row and active_row != self.last_active_row:
            if self.btn_autoscroll.isChecked():
                # Posunout scrollbar tak, aby widget byl nahoře
                # row.y() vrací pozici widgetu uvnitř scroll_content
                self.scroll.verticalScrollBar().setValue(active_row.y())
            
            self.last_active_row = active_row

    # --- Zbytek metod beze změny logiky, jen kontext ---
    
    def open_video(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Vybrat Video")
        if fname:
            self.player.setSource(QUrl.fromLocalFile(fname))
            self.player.setPlaybackRate(1.0)
            try:
                timestamp = os.path.getmtime(fname)
                self.video_start_time = datetime.fromtimestamp(timestamp)
            except Exception:
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

    def seek_relative(self, ms):
        self.player.setPosition(self.player.position() + ms)

    def change_speed(self):
        speed = float(self.speed_combo.currentText().replace('x', ''))
        self.player.setPlaybackRate(speed)

    def add_subtitle_at_current(self):
        curr_ms = self.player.position()
        curr_sec = curr_ms / 1000.0
        
        new_item = {
            "start": curr_sec,
            "end": curr_sec + 2.0,
            "text": "Nový titulek"
        }
        
        row = SubtitleRow(new_item, self.player, self.delete_row)
        
        insert_idx = len(self.subtitle_rows)
        for i, r in enumerate(self.subtitle_rows):
            if r.start_sec > new_item['start']:
                insert_idx = i
                break
        
        self.scroll_layout.insertWidget(insert_idx, row)
        self.subtitle_rows.insert(insert_idx, row)
        
        # Seřadit pole, aby fungovala logika highlightu
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
                row = SubtitleRow(item, self.player, self.delete_row)
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
            QMessageBox.information(self, "Uloženo", "Soubor byl uložen.")
        except Exception as e:
            QMessageBox.critical(self, "Chyba", str(e))

    def process_all(self):
        for row in self.subtitle_rows:
            row.run_ai_single()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion") 
    window = MainWindow()
    window.show()
    sys.exit(app.exec())