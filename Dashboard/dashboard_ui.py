import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton
)
from PyQt6.QtCore import Qt

from database import load_history, get_stats, load_player_name

BG_DARK = "#1f1105"
BG_PANEL = "#1D0D01"
SEPARATOR = "#4f432f"
TEXT_LIGHT = "#f5e9c5"
ACCENT = "#d4af37"
BUTTON_BG = "#7c6429"
BUTTON_BG_HOVER = "#9b7c2f"


class DashboardUI(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Dashboard - Rek Game")
        self.resize(800, 500)

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {BG_DARK};
                color: {TEXT_LIGHT};
                font-size: 14px;
                font-family: 'Khmer OS Muol Light';
            }}
            QTableWidget {{
                background-color: {BG_PANEL};
                color: {TEXT_LIGHT};
                border: 1px solid {SEPARATOR};
                gridline-color: {SEPARATOR};
            }}
            QHeaderView::section {{
                background-color: {BG_PANEL};
                color: {TEXT_LIGHT};
                border: 1px solid {SEPARATOR};
                padding: 8px;
            }}
            QPushButton {{
                background-color: {BUTTON_BG};
                border: 1px solid {ACCENT};
                padding: 10px;
                color: {TEXT_LIGHT};
                border-radius: 12px;
                font-family: 'Khmer OS Muol Light';
            }}
            QPushButton:hover {{
                background-color: {BUTTON_BG_HOVER};
            }}
        """)

        layout = QVBoxLayout(self)

        # 👤 Player Name
        player = load_player_name() or "Player"
        self.lbl_player = QLabel(f"👤 {player}")
        self.lbl_player.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_player)

        # 🏆 Stats
        wins, loses = get_stats()
        self.lbl_stats = QLabel(f"🏆 Wins: {wins}   ❌ Loses: {loses}")
        self.lbl_stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_stats)

        # 📜 History Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ["Player", "Mode", "Result", "Time"]
        )

        layout.addWidget(self.table)

        # 🔄 Load button
        btn = QPushButton("Load History")
        btn.clicked.connect(self.load_data)
        layout.addWidget(btn)

        self.load_data()

    def load_data(self):
        data = load_history()

        self.table.setRowCount(len(data))

        for row_idx, row in enumerate(data):
            for col_idx, value in enumerate(row):
                self.table.setItem(
                    row_idx,
                    col_idx,
                    QTableWidgetItem(str(value))
                )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DashboardUI()
    win.show()
    sys.exit(app.exec())