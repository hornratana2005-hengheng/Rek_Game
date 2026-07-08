import sys
import sqlite3
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QTextEdit, 
                             QGroupBox, QStatusBar)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

class KhmerGrammarCleanApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_database()
        self.tokens = [] 
        self.init_ui()

    def init_database(self):
        """បង្កើត និងផ្ទុកទិន្នន័យពាក្យក្នុង SQLite Memory"""
        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS word_bank (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word_kh TEXT NOT NULL UNIQUE,
                word_en TEXT NOT NULL,
                category_kh TEXT NOT NULL,
                category_en TEXT NOT NULL
            )
        ''')
        
        # ធនាគារពាក្យគំរូ
        default_words = [
            ('សិស្ស', 'Students', 'នាម', 'Noun'),
            ('គ្រូបង្រៀន', 'The teacher', 'នាម', 'Noun'),
            ('ពួកយើង', 'We', 'សព្វនាម', 'Pronoun'),
            ('ខ្ញុំ', 'I', 'សព្វនាម', 'Pronoun'),
            ('រៀន', 'study', 'កិរិយាសព្ទ', 'Verb'),
            ('ញ៉ាំ', 'eat', 'កិរិយាសព្ទ', 'Verb'),
            ('មើល', 'watch', 'កិរិយាសព្ទ', 'Verb'),
            ('ភាសាខ្មែរ', 'Khmer language', 'នាម', 'Noun'),
            ('បាយ', 'rice', 'នាម', 'Noun'),
            ('សៀវភៅ', 'books', 'នាម', 'Noun'),
            ('នៅសាលារៀន', 'at school', 'គុណកិរិយា', 'Adverb'),
            ('យ៉ាងសប្បាយ', 'happily', 'គុណកិរិយា', 'Adverb'),
            ('ជារៀងរាល់ថ្ងៃ', 'every day', 'គុណកិរិយា', 'Adverb'),
            ('នៅផ្ទះ', 'at home', 'គុណកិរិយា', 'Adverb'),
            ('ទៅសាលារៀន', 'go to school', 'ឃ្លាកិរិយាសព្ទ', 'Verb Phrase'),
        ]
        self.cursor.executemany(
            'INSERT OR IGNORE INTO word_bank (word_kh, word_en, category_kh, category_en) VALUES (?, ?, ?, ?)', 
            default_words
        )
        self.conn.commit()

    def init_ui(self):
        self.setWindowTitle("Khmer Grammar & Translation Tool")
        self.setGeometry(100, 100, 950, 650)
        
        # ប្រើពុម្ពអក្សរធម្មតាមិនដិត (Not Bold)
        self.app_font = QFont("Khmer OS Battambang", 11)
        self.setFont(self.app_font)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # =========================================================================
        # ផ្នែកខាងលើ៖ ប៊ូតុងបញ្ជាទាំង ៤
        # =========================================================================
        buttons_group = QGroupBox("ជ្រើសរើសមុខងារដើម្បីបង្ហាញទិន្នន័យ")
        buttons_group.setFont(self.app_font)
        buttons_layout = QHBoxLayout(buttons_group)

        self.btn_trans = QPushButton("🌐 បកប្រែ (Translate)")
        self.btn_grammar = QPushButton("📐 វេយ្យាករណ៍ (Grammar)")
        self.btn_bank = QPushButton("📚 ធនាគារពាក្យ (Word Bank)")
        self.btn_result = QPushButton("📊 លទ្ធផល (Result Status)")

        for btn in [self.btn_trans, self.btn_grammar, self.btn_bank, self.btn_result]:
            btn.setFont(self.app_font)
            btn.setStyleSheet("padding: 10px; background-color: #F0F0F0; border: 1px solid #CCCCCC; border-radius: 4px; font-weight: normal;")
            buttons_layout.addWidget(btn)

        main_layout.addWidget(buttons_group)

        # ផ្ទាំងបង្ហាញព័ត៌មានលម្អិត
        self.display_panel = QGroupBox("ផ្ទាំងបង្ហាញព័ត៌មានលម្អិត")
        self.display_panel.setFont(self.app_font)
        panel_layout = QVBoxLayout(self.display_panel)
        
        self.txt_display = QTextEdit()
        self.txt_display.setReadOnly(True)
        self.txt_display.setFont(self.app_font)
        self.txt_display.setStyleSheet("background-color: #FFFFFF; color: #333333; font-weight: normal;")
        panel_layout.addWidget(self.txt_display)
        
        main_layout.addWidget(self.display_panel, 4)

        # ភ្ជាប់ប៊ូតុង
        self.btn_trans.clicked.connect(self.show_translation)
        self.btn_grammar.clicked.connect(self.show_grammar)
        self.btn_bank.clicked.connect(self.show_word_bank)
        self.btn_result.clicked.connect(self.show_result_status)

        # =========================================================================
        # ផ្នែកខាងក្រោម៖ ទម្រង់បញ្ចូល និងបង្ហាញអត្ថបទ
        # =========================================================================
        bottom_form_group = QGroupBox("ទម្រង់បញ្ចូល និងបង្ហាញអត្ថបទ (Input/Output Form)")
        bottom_form_group.setFont(self.app_font)
        bottom_layout = QVBoxLayout(bottom_form_group)

        lbl_kh = QLabel("អត្ថបទខ្មែរ (Khmer Input)៖")
        lbl_kh.setFont(self.app_font)
        bottom_layout.addWidget(lbl_kh)
        
        self.input_khmer = QTextEdit()
        self.input_khmer.setFont(self.app_font)
        self.input_khmer.setPlaceholderText("វាយល្បះខ្មែរនៅទីនេះ... រួចចុចប៊ូតុង 'វិភាគអត្ថបទ' ខាងក្រោម")
        self.input_khmer.setMaximumHeight(75)
        self.input_khmer.setStyleSheet("font-weight: normal;")
        bottom_layout.addWidget(self.input_khmer)

        self.btn_process = QPushButton("⚡ វិភាគអត្ថបទ (Analyze Input)")
        self.btn_process.setFont(self.app_font)
        self.btn_process.setStyleSheet("background-color: #0078D4; color: white; padding: 8px; font-weight: normal;")
        self.btn_process.clicked.connect(self.process_logic)
        bottom_layout.addWidget(self.btn_process)

        lbl_en = QLabel("អត្ថបទអង់គ្លេស (English Output)៖")
        lbl_en.setFont(self.app_font)
        bottom_layout.addWidget(lbl_en)
        
        self.output_english = QTextEdit()
        self.output_english.setReadOnly(True)
        self.output_english.setFont(self.app_font)
        self.output_english.setMaximumHeight(75)
        self.output_english.setStyleSheet("background-color: #F3F2F1; color: #004B87; font-weight: normal;")
        bottom_layout.addWidget(self.output_english)

        main_layout.addWidget(bottom_form_group, 3)

        # StatusBar
        self.statusBar = QStatusBar()
        self.statusBar.setFont(self.app_font)
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("សូមបញ្ចូលល្បះខ្មែរ រួចចុច 'វិភាគអត្ថបទ'")
        
        self.show_word_bank()

    # =========================================================================
    # មុខងារគ្រប់គ្រង Logic
    # =========================================================================

    def process_logic(self):
        text = self.input_khmer.toPlainText().strip()
        if not text:
            self.statusBar.showMessage("សូមបញ្ចូលអត្ថបទខ្មែរជាមុនសិន!")
            return

        self.cursor.execute("SELECT word_kh, word_en, category_kh, category_en FROM word_bank")
        db_words = self.cursor.fetchall()
        db_words.sort(key=lambda x: len(x[0]), reverse=True)

        self.tokens = []
        temp_text = text
        
        while len(temp_text) > 0:
            match_found = False
            for kh, en, cat_kh, cat_en in db_words:
                if temp_text.startswith(kh):
                    self.tokens.append({'kh': kh, 'en': en, 'cat_kh': cat_kh, 'cat_en': cat_en})
                    temp_text = temp_text[len(kh):].strip()
                    match_found = True
                    break
            if not match_found:
                # 🎯 ប្រសិនបើរករៀបពាក្យមិនឃើញក្នុងទិន្នន័យ SQLite ឱ្យដាក់ថា "មិនមាន"
                self.tokens.append({'kh': temp_text[0], 'en': temp_text[0], 'cat_kh': 'មិនមាន', 'cat_en': 'Unknown'})
                temp_text = temp_text[1:].strip()

        # បង្កើតល្បះបកប្រែ (មិនបូកបញ្ចូលពាក្យដែលរកមិនឃើញ ឬ "Unknown" ទេ)
        en_words = [t['en'] for t in self.tokens if t['cat_en'] != 'Unknown']
        translated_sentence = " ".join(en_words) + "."
        self.output_english.setText(translated_sentence)

        self.show_translation()
        self.statusBar.showMessage("វិភាគជោគជ័យ!")

    def highlight_active_button(self, active_button):
        for btn in [self.btn_trans, self.btn_grammar, self.btn_bank, self.btn_result]:
            if btn == active_button:
                btn.setStyleSheet("padding: 10px; background-color: #0078D4; color: white; border: 1px solid #005A9E; border-radius: 4px; font-weight: normal;")
            else:
                btn.setStyleSheet("padding: 10px; background-color: #F0F0F0; color: black; border: 1px solid #CCCCCC; border-radius: 4px; font-weight: normal;")

    def show_translation(self):
        self.highlight_active_button(self.btn_trans)
        if not self.tokens:
            self.txt_display.setText("មិនទាន់មានទិន្នន័យ។ សូមវាយបញ្ចូលអត្ថបទរួចចុច 'វិភាគអត្ថបទ' ជាមុនសិន!")
            return
        
        en_words = [t['en'] for t in self.tokens if t['cat_en'] != 'Unknown']
        translated_sentence = " ".join(en_words) + "."
        
        display = "🌐 លទ្ធផលបកប្រែ\n\n"
        display += f"អត្ថបទខ្មែរ៖ \n{self.input_khmer.toPlainText()}\n\n"
        display += f"អត្ថបទអង់គ្លេស៖\n{translated_sentence}"
        self.txt_display.setText(display)

    def show_grammar(self):
        self.highlight_active_button(self.btn_grammar)
        if not self.tokens:
            self.txt_display.setText("មិនទាន់មានទិន្នន័យ។")
            return

        kh_struct = [t['cat_kh'] for t in self.tokens]
        en_struct = [t['cat_en'] for t in self.tokens]

        display = "📐 ការវិភាគរចនាសម្ព័ន្ធវេយ្យាករណ៍\n\n"
        display += f"ទម្រង់ល្បះខ្មែរ៖ \n" + " + ".join(kh_struct) + "\n\n"
        display += f"ទម្រង់ល្បះអង់គ្លេស៖\n" + " + ".join(en_struct)
        self.txt_display.setText(display)

    def show_word_bank(self):
        self.highlight_active_button(self.btn_bank)
        if not self.tokens:
            self.cursor.execute("SELECT word_kh, word_en, category_kh, category_en FROM word_bank ORDER BY category_kh")
            rows = self.cursor.fetchall()
            display = "📚 ធនាគារពាក្យទូទៅក្នុងប្រព័ន្ធ SQLite\n\n"
            for kh, en, cat_kh, cat_en in rows:
                display += f"• {kh} ({cat_kh}) : {en} ({cat_en})\n"
            self.txt_display.setText(display)
            return

        display = "📚 ធនាគារពាក្យដែលបានបំបែកចេញពីល្បះ\n\n"
        for t in self.tokens:
            display += f"• {t['kh']} ({t['cat_kh']}) : {t['en']} ({t['cat_en']})\n"
        self.txt_display.setText(display)

    def show_result_status(self):
        self.highlight_active_button(self.btn_result)
        if not self.tokens:
            self.txt_display.setText("មិនទាន់មានប្រតិបត្តិការវិភាគនៅឡើយទេ។")
            return

        display = "📊 ស្ថានភាពលទ្ធផល\n\n"
        display += f"• ការវិភាគ៖ ជោគជ័យ\n"
        display += f"• ចំនួនពាក្យដែលបានបំបែក៖ {len(self.tokens)} ពាក្យ\n"
        display += f"• ទិន្នន័យ៖ ផ្ទៀងផ្ទាត់ជាមួយ SQLite រួចរាល់\n"
        self.txt_display.setText(display)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    win = KhmerGrammarCleanApp()
    win.show()
    sys.exit(app.exec())