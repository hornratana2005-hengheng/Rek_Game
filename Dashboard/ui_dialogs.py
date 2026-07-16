from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt6.QtCore import Qt

BG_DARK = "#1f1105"
BG_PANEL = "#1D0D01"
SEPARATOR = "#4f432f"
TEXT_LIGHT = "#f5e9c5"
ACCENT = "#d4af37"
PIECE_GREEN = "#4CAF50"
PIECE_LIGHT = "#8BC34A"
BUTTON_BG = "#7c6429"
BUTTON_BG_HOVER = "#9b7c2f"


class EnterNameDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Enter Name")
        self.setFixedSize(400, 250)

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {BG_DARK};
                border: 2px solid {ACCENT};
                border-radius: 18px;
            }}
            QLabel {{
                color: {TEXT_LIGHT};
                font-size: 18px;
                font-family: 'Khmer OS Muol Light';
            }}
            QLineEdit {{
                background-color: {BG_PANEL};
                color: {TEXT_LIGHT};
                border: 1px solid {SEPARATOR};
                padding: 12px;
                border-radius: 12px;
                font-size: 16px;
            }}
            QPushButton {{
                background-color: {BUTTON_BG};
                color: {TEXT_LIGHT};
                font-weight: bold;
                padding: 10px;
                border-radius: 12px;
                border: 1px solid {ACCENT};
                font-family: 'Khmer OS Muol Light';
            }}
            QPushButton:hover {{
                background-color: {BUTTON_BG_HOVER};
            }}
        """)

        layout = QVBoxLayout(self)

        title = QLabel("បញ្ចូលឈ្មោះរបស់អ្នក")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Your Name...")

        btn = QPushButton("START")

        btn.clicked.connect(self.accept)

        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(self.input)
        layout.addWidget(btn)
        layout.addStretch()

    def get_name(self):
        return self.input.text().strip()