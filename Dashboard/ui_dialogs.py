from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt6.QtCore import Qt


class EnterNameDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Enter Name")
        self.setFixedSize(400, 250)

        self.setStyleSheet("""
            QDialog {
                background-color: #110903;
                border: 2px solid #ca8b47;
                border-radius: 15px;
            }
            QLabel {
                color: #ca8b47;
                font-size: 18px;
            }
            QLineEdit {
                background-color: #1f1105;
                color: white;
                border: 1px solid #6a4b18;
                padding: 10px;
                border-radius: 8px;
                font-size: 16px;
            }
            QPushButton {
                background-color: #ca8b47;
                color: black;
                font-weight: bold;
                padding: 10px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #e6b800;
            }
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