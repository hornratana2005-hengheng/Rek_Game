import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton
)
from PyQt6.QtCore import Qt

from database import load_history, get_stats, load_player_name


class DashboardUI(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Dashboard - Rek Game")
        self.resize(800, 500)

        self.setStyleSheet("""
            QWidget {
                background-color: #110903;
                color: #ecc06a;
                font-size: 14px;
            }
            QTableWidget {
                background-color: #1f1105;
                color: white;
                border: 1px solid #6a4b18;
            }
            QPushButton {
                background-color: #381c06;
                border: 1px solid #6a4b18;
                padding: 8px;
                color: #ecc06a;
            }
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