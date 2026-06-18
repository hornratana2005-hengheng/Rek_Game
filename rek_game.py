import sys
import copy
import json
import random
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, 
                             QPushButton, QFrame, QVBoxLayout, QHBoxLayout, 
                             QGridLayout, QMessageBox, QTextEdit)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont,QPixmap
from PyQt6.QtWidgets import QDialog
# ==========================================
# ១. ការកំណត់ THEME & COLOR
# ==========================================
BG_DARK = "#1f1105"
BG_PANEL = "#110903"
BG_BOARD_CONTAINER = "#381c06"
GOLD_BORDER = "#6a4b18"
BOARD_LIGHT = "#ca8b47"
BOARD_DARK = "#8f5521"

# ==========================================
# ២. LOGIC គ្រប់គ្រងក្តារអុក (BOARD LOGIC)
# ==========================================
class BoardLogic:
    def __init__(self):
        self.grid = [[None for _ in range(8)] for _ in range(8)]
        self.history = []
        self.reset_board()
    def reset_board(self):
        self.grid = [[None for _ in range(8)] for _ in range(8)]
        self.history = []

        # 🟢 ក្រុមខាងលើ (G)
        for c in range(7):           # ooooooo.
            self.grid[0][c] = 'G'

        self.grid[1][7] = 'GK'       # .......O

        for c in range(8):           # oooooooo
            self.grid[2][c] = 'G'

        # ជួរកណ្ដាលទំនេរ
        # row 3, row 4 = None

    # 🟡 ក្រុមខាងក្រោម (L)
        for c in range(8):           # oooooooo
            self.grid[5][c] = 'L'

            self.grid[6][0] = 'LK'       # O.......

        for c in range(1, 8):        # .ooooooo
            self.grid[7][c] = 'L'

    def get_piece(self, r, c): 
        return self.grid[r][c]

    def is_valid_move(self, sr, sc, er, ec, player):
        piece = self.grid[sr][sc]
        if not piece or not piece.startswith(player): return False
        if self.grid[er][ec] is not None: return False
        if sr != er and sc != ec: return False 
        
        if sr == er:
            step = 1 if ec > sc else -1
            for c in range(sc + step, ec, step):
                if self.grid[sr][c] is not None: return False
        else:
            step = 1 if er > sr else -1
            for r in range(sr + step, er, step):
                if self.grid[r][sc] is not None: return False
        return True

    def save_state(self): 
        self.history.append(copy.deepcopy(self.grid))

    def undo(self):
        if self.history:
            self.grid = self.history.pop()
            return True
        return False

    def make_move(self, sr, sc, er, ec):
        piece = self.grid[sr][sc]
        self.grid[sr][sc] = None
        self.grid[er][ec] = piece
        
        captured = []
        captured.extend(self._check_rek(er, ec, piece[0]))
        captured.extend(self._check_gnyap(piece[0]))
        for r, c in captured: 
            self.grid[r][c] = None
        return captured

    def _check_rek(self, r, c, player_prefix):
        enemy = 'L' if player_prefix == 'G' else 'G'
        cap = []
        if 0 <= c - 1 and c + 1 < 8:
            if self.grid[r][c-1] and self.grid[r][c-1].startswith(enemy) and \
               self.grid[r][c+1] and self.grid[r][c+1].startswith(enemy):
                cap.extend([(r, c-1), (r, c+1)])
        if 0 <= r - 1 and r + 1 < 8:
            if self.grid[r-1][c] and self.grid[r-1][c].startswith(enemy) and \
               self.grid[r+1][c] and self.grid[r+1][c].startswith(enemy):
                cap.extend([(r-1, c), (r+1, c)])
        return cap

    def _check_gnyap(self, player_prefix):
        enemy = 'L' if player_prefix == 'G' else 'G'
        visited = set()
        to_remove = []

        def has_move(r, c):
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                for step in range(1, 8):
                    nr, nc = r + dr*step, c + dc*step

                    if not (0 <= nr < 8 and 0 <= nc < 8):
                        break

                    if self.grid[nr][nc] is None:
                        return True
                    else:
                        break
            return False

        def bfs(sr, sc):
            stack = [(sr, sc)]
            group = []

            while stack:
                r, c = stack.pop()

                if (r, c) in visited:
                    continue
                visited.add((r, c))
                group.append((r, c))

                for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nr, nc = r + dr, c + dc

                    if 0 <= nr < 8 and 0 <= nc < 8:
                        if self.grid[nr][nc] and self.grid[nr][nc].startswith(enemy):
                            stack.append((nr, nc))

            return group

        # find all enemy groups
        for r in range(8):
            for c in range(8):
                if (r, c) in visited:
                    continue

                p = self.grid[r][c]
                if not p or not p.startswith(enemy):
                    continue

                group = bfs(r, c)

                # check if ANY piece in group can move
                if not any(has_move(x, y) for x, y in group):
                    to_remove.extend(group)

        return to_remove
    def count_pieces(self):
        g, l, gk, lk = 0, 0, False, False
        for r in range(8):
            for c in range(8):
                p = self.grid[r][c]
                if p and p.startswith('G'): 
                    g += 1
                    if 'K' in p: gk = True
                elif p and p.startswith('L'): 
                    l += 1
                    if 'K' in p: lk = True
        return g, l, gk, lk

# ==========================================
# ៣. ភ្នាក់ងារបញ្ញាសិប្បនិម្មិត (AI AGENT)
# ==========================================
class AIAgent:
    def __init__(self, player_prefix='L'):
        self.player_prefix = player_prefix

    def calculate_move(self, board_logic):
        valid_moves = []
        for r in range(8):
            for c in range(8):
                piece = board_logic.get_piece(r, c)
                if piece and piece.startswith(self.player_prefix):
                    for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
                        for step in range(1, 8):
                            nr, nc = r + dr * step, c + dc * step
                            if 0 <= nr < 8 and 0 <= nc < 8:
                                if board_logic.is_valid_move(r, c, nr, nc, self.player_prefix):
                                    valid_moves.append(((r, c), (nr, nc)))
                                else: break
                            else: break
        if not valid_moves: return None
        
        best_move = random.choice(valid_moves)
        max_captured = -1
        for move in valid_moves:
            (sr, sc), (er, ec) = move
            temp_grid = copy.deepcopy(board_logic.grid)
            piece = temp_grid[sr][sc]
            temp_grid[sr][sc] = None
            temp_grid[er][ec] = piece
            
            enemy = 'G'
            cap = 0
            if 0 <= ec - 1 and ec + 1 < 8:
                if temp_grid[er][ec-1] and temp_grid[er][ec-1].startswith(enemy) and temp_grid[er][ec+1] and temp_grid[er][ec+1].startswith(enemy): cap += 2
            if 0 <= er - 1 and er + 1 < 8:
                if temp_grid[er-1][ec] and temp_grid[er-1][ec].startswith(enemy) and temp_grid[er+1][ec] and temp_grid[er+1][ec].startswith(enemy): cap += 2
            if cap > max_captured:
                max_captured = cap
                best_move = move
        return best_move

# ==========================================
# ៤. សមាសភាគក្រឡាក្តារអុក (BOARD WIDGET COMPONENTS)
# ==========================================
class ClickableCell(QFrame):
    cell_pressed = pyqtSignal(int, int)
    def __init__(self, r, c):
        super().__init__()
        self.r, self.c = r, c
        self.setFixedSize(65, 65)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.cell_pressed.emit(self.r, self.c)

class BoardWidget(QWidget):
    square_clicked = pyqtSignal(int, int)
    def __init__(self):
        super().__init__()
        self.cells = {}
        self.init_ui()

    def init_ui(self):
        layout = QGridLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)
        
        for r in range(8):
            for c in range(8):
                cell = ClickableCell(r, c)
                bg = BOARD_LIGHT if (r + c) % 2 == 0 else BOARD_DARK
                cell.setStyleSheet(f"background-color: {bg}; border-radius: 12px;")
                cell.cell_pressed.connect(self.square_clicked.emit)
                
                cell_layout = QVBoxLayout(cell)
                cell_layout.setContentsMargins(0, 0, 0, 0)
                cell_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                
                layout.addWidget(cell, r, c)
                self.cells[(r, c)] = cell

# ==========================================
# ៥. គំនូរកូនអុក (PIECE DRAWING)
# ==========================================
class Piece(QWidget):
    def __init__(self, color="green", king=False, is_selected=False):
        super().__init__()
        self.color = color
        self.king = king
        self.is_selected = is_selected
        self.setFixedSize(48, 48)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self.is_selected:
            painter.setBrush(QBrush(QColor(255, 255, 255, 120)))
            painter.setPen(QPen(QColor("#ca8b47"), 2, Qt.PenStyle.SolidLine))
            painter.drawEllipse(1, 1, 46, 46)

        fill = QColor("#009a49") if self.color == "green" else QColor("#b4cc33")
        border = QColor("#ffffff") if self.king else (QColor("#006633") if self.color == "green" else QColor("#778822"))
        
        painter.setBrush(QBrush(fill))
        painter.setPen(QPen(border, 2))
        painter.drawEllipse(4, 4, 40, 40)
        
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(255, 255, 255, 80), 1))
        painter.drawEllipse(8, 8, 32, 32)

        if self.king:
            painter.setPen(QPen(QColor("blue"), 2))
            painter.setFont(QFont("Khmer OS Muol Light", 13))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "♔")

# ==========================================
# ៦. ផ្ទាំងបង្ហាញច្បាប់លេង (RULES UI)
# ==========================================
class RulesUI(QWidget):
    
    def __init__(self, controller, source="home"):
        super().__init__()

        self.controller = controller
        self.source = source
        super().__init__()
        self.controller = controller
        self.setWindowTitle("ច្បាប់លេងល្បែងរែក - Game Rules")
        self.resize(1000, 750)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet(f"background-color: {BG_DARK};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)

        title = QLabel("ច្បាប់លេងល្បែងរែកខ្មែរ")
        title.setStyleSheet("color: #ca8b47; font-size: 28px; font-family: 'Khmer OS Muol Light';")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        content = QTextEdit()
        content.setReadOnly(True)
        content.setStyleSheet("background-color: #110903; color: #ca8b47; font-size: 16px; border: 2px solid #6a4b18; padding: 15px; line-height: 30px;")
        
        rules_text = (
            "១. ការរៀបចំក្តារដំបូង៖ កូនអុកមាន ២ ពណ៌ តម្រៀបជាន់គ្នាជាពីរជួរ និង ស្តេចនៅជួរទី២ និងទី៧ តាមទម្រង់ Grid លម្អិត។\n\n"
            "២. របៀបផ្លាស់ទី (Long-Range Move)៖ កូនអុកអាចរំកិលទៅមុខ ថយក្រោយ ឆ្វេង ឬ ស្តាំ បានច្រើនក្រឡាកក្នុងពេលតែមួយ ឱ្យតែផ្លូវត្រង់នោះទំនេរគ្មានគ្រាប់បាំង។\n\n"
            "៣. ក្បួនស៊ីរែក (RÈK)៖ នៅពេលអ្នករំកិលកូនអុកទៅចំកណ្តាលចន្លោះកូនសត្រូវពីរ "
            "នោះអ្នកនឹងរែកស៊ីកូនសត្រូវទាំងពីរដាច់ចេញពីក្តារភ្លាមៗ។\n\n"
            "៤. ក្បួនឡោមព័ទ្ធ (GNYAP)៖ នៅពេលកូនអុករបស់សត្រូវត្រូវបានព័ទ្ធជុំវិញគ្រប់ច្រកល្ហក គ្មានផ្លូវរត់ចេញបាន វានឹងត្រូវងាប់ដោយស្វ័យប្រវត្តិ。\n\n"
            "៥. លក្ខខណ្ឌឈ្នះ៖ អ្នកដែលបានស៊ីស្តេច «♔» របស់សត្រូវមុន ឬស៊ីគ្រាប់សត្រូវអស់ពីក្តារ គឺជាអ្នកឈ្នះ"
        )
        content.setPlainText(rules_text)
        layout.addWidget(content)

        btn_back = QPushButton("បិទ")
        btn_back.setFixedSize(250, 50)
        btn_back.setStyleSheet(f"background-color: #381c06; color: #ca8b47; border: 1px solid {GOLD_BORDER}; border-radius: 8px; font-weight: bold;")
        btn_back.clicked.connect(self._back)
        layout.addWidget(btn_back, alignment=Qt.AlignmentFlag.AlignCenter)

    def _back(self):

        if self.source == "game":

            self.controller.game_window.show()
            self.controller.game_window.timer.start(1000)

        else:

            self.controller.home_window.show()

        self.close()
#Show Information
class InformationDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ព័ត៌មានហ្គេម")
        self.resize(700, 500)

        self.setStyleSheet("""
            QDialog {
                background-color: #110903;
                border: 2px solid #6a4b18;
            }

            QLabel {
                color: #ca8b47;
            }

            QTextEdit {
                background-color: #1f1105;
                color: white;
                border: 1px solid #6a4b18;
                padding: 10px;
            }

            QPushButton {
                background-color: #381c06;
                color: #ca8b47;
                border: 1px solid #6a4b18;
                border-radius: 8px;
                padding: 8px;
            }
        """)

        layout = QVBoxLayout(self)

        title = QLabel("ព័ត៌មានអំពីល្បែងរែក")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-size:24px;
            font-family:'Khmer OS Muol Light';
        """)

        text = QTextEdit()
        text.setReadOnly(True)

        text.setPlainText("""
ល្បែងរែក (RÈK)

ល្បែងរែក គឺជាល្បែងក្តារបុរាណខ្មែរមួយ ដែលមានប្រវត្តិយូរលង់មកហើយ។ ល្បែងនេះត្រូវបានលេងដោយមនុស្សពីរនាក់ លើក្តារទំហំ ៨x៨ ក្រឡា។ ពាក្យ “រែក” មានន័យថា ការសែងរបស់ដោយប្រើដងរែក ដែលមានបន្ទុកនៅសងខាង។ ឈ្មោះនេះត្រូវបានយកមកប្រើក្នុងល្បែង ដើម្បីប្រៀបធៀបការចាប់គ្រាប់សត្រូវទៅនឹងការសែងយកបន្ទុក។
តាមការសិក្សា និងការប្រាប់តៗគ្នា ល្បែងនេះធ្លាប់មានប្រជាប្រិយភាពក្នុងចំណោមទាហានខ្មែរ ព្រោះវាជាល្បែងដែលត្រូវការការគិតយុទ្ធសាស្ត្រ និងការរៀបចំផែនការ។ ទាហានអាចប្រើល្បែងនេះសម្រាប់ហ្វឹកហាត់ការគិត និងការសម្រេចចិត្ត។ ល្បែងរែកមានគ្រាប់សរុប ៣២ គ្រាប់ ចែកជា ២ ភាគី។ មួយភាគីមានស្តេច ១ និងទាហាន ១៥។ គ្រាប់ទាំងអស់អាចផ្លាស់ទីដូចទូកក្នុងអុក។ គោលបំណងសំខាន់គឺការចាប់ស្តេចរបស់គូប្រកួត ។


Developed with PyQt6
Version 1.0

ប្រវត្តិ Python

Python គឺជាភាសាសរសេរកម្មវិធីកម្រិតខ្ពស់ (High-Level Programming Language) ដែលត្រូវបានបង្កើតឡើងដោយ Guido van Rossum នៅចុងទសវត្សរ៍ឆ្នាំ 1980 និងបានចេញផ្សាយជាផ្លូវការលើកដំបូងនៅឆ្នាំ 1991។ គោលបំណងនៃការបង្កើត Python គឺដើម្បីបង្កើតភាសាកម្មវិធីដែលមានលក្ខណៈសាមញ្ញ ងាយស្រួលអាន និងងាយស្រួលសរសេរ។ ឈ្មោះ "Python" មិនមែនមានប្រភពពីសត្វពស់នោះទេ ប៉ុន្តែត្រូវបានដាក់តាមកម្មវិធីកំប្លែងអង់គ្លេសមួយឈ្មោះ Monty Python's Flying Circus ដែល Guido van Rossum ចូលចិត្ត។
ចាប់តាំងពីការចេញផ្សាយលើកដំបូង Python បានអភិវឌ្ឍជាបន្តបន្ទាប់ និងបានចេញ Version ជាច្រើន។ Python 2 បានក្លាយជាជំនាន់ដែលមានការពេញនិយមយ៉ាងខ្លាំង ខណៈ Python 3 ដែលចេញនៅឆ្នាំ 2008 បាននាំមកនូវការកែលម្អជាច្រើនផ្នែកទាំងប្រសិទ្ធភាព និងសុវត្ថិភាព ។ បច្ចុប្បន្ន Python គឺជាភាសាកម្មវិធីមួយក្នុងចំណោមភាសាដែលពេញនិយមបំផុតនៅលើពិភពលោក ហើយត្រូវបានប្រើប្រាស់ក្នុងវិស័យជាច្រើនដូចជា Web Development, Data Science, Machine Learning, Artificial Intelligence, Cybersecurity និង Desktop Application Development។


ប្រវត្តិ PyQt6

PyQt6 គឺជា Library សម្រាប់ Python ដែលអនុញ្ញាតឱ្យអ្នកអភិវឌ្ឍកម្មវិធីអាចបង្កើត Graphical User Interface (GUI) បានយ៉ាងងាយស្រួល។ PyQt6 ត្រូវបានបង្កើតឡើងដោយ Riverbank Computing ដែលបានបង្កើត Python Binding សម្រាប់ Qt Framework។
ប្រវត្តិរបស់ PyQt ចាប់ផ្តើមនៅឆ្នាំ 1998 នៅពេលដែល Riverbank Computing បានបញ្ចេញ PyQt ជំនាន់ដំបូង ដើម្បីអនុញ្ញាតឱ្យអ្នកសរសេរកម្មវិធី Python អាចប្រើប្រាស់ Qt Framework ក្នុងការបង្កើតកម្មវិធី Desktop ដែលមានផ្ទាំងក្រាហ្វិក។
បន្ទាប់ពីជោគជ័យនៃ PyQt4 និង PyQt5 ក្រុមអភិវឌ្ឍន៍បានបញ្ចេញ PyQt6 នៅឆ្នាំ 2021 ដោយផ្អែកលើ Qt 6។ PyQt6 បាននាំមកនូវការកែលម្អជាច្រើន ដូចជា ការគាំទ្របច្ចេកវិទ្យាថ្មីៗ ការបង្កើនប្រសិទ្ធភាព និងការគាំទ្រប្រព័ន្ធប្រតិបត្តិការទំនើប។
សព្វថ្ងៃ PyQt6 ត្រូវបានប្រើប្រាស់យ៉ាងទូលំទូលាយសម្រាប់បង្កើតកម្មវិធី Desktop ដែលមានរូបរាងទំនើប និងដំណើរការបានលើ Windows, Linux និង macOS ដោយប្រើកូដតែមួយ។

        """)

        btn = QPushButton("បិទ")
        btn.clicked.connect(self.accept)

        layout.addWidget(title)
        layout.addWidget(text)
        layout.addWidget(btn)
#Winner#
class WinnerDialog(QDialog):
    def __init__(self, winner):
        super().__init__()

        self.setWindowTitle("Game Over")
        self.setFixedSize(450, 280)

        self.setStyleSheet("""
            QDialog {
                background-color: #110903;
                border: 3px solid #ca8b47;
                border-radius: 20px;
            }

            QLabel {
                color: #f7e6c4;
                background: transparent;
            }

            QPushButton {
                background-color: #009a49;
                color: white;
                border-radius: 10px;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #00b85a;
            }
        """)

        layout = QVBoxLayout(self)

        trophy = QLabel("👑")
        trophy.setAlignment(Qt.AlignmentFlag.AlignCenter)
        trophy.setStyleSheet("font-size: 64px;")

        title = QLabel("YOU WIN!")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #ca8b47;
        """)

        text = QLabel(winner)
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text.setWordWrap(True)
        text.setStyleSheet("font-size: 16px;")

        btn = QPushButton("OK")
        btn.setFixedHeight(45)
        btn.clicked.connect(self.accept)

        layout.addStretch()
        layout.addWidget(trophy)
        layout.addWidget(title)
        layout.addSpacing(10)
        layout.addWidget(text)
        layout.addStretch()
        layout.addWidget(btn)
# ==========================================
# ៧. ផ្ទាំងលេងហ្គេមចម្បង (MAIN GAME UI)
# ==========================================
class RekGameUI(QMainWindow):
    def __init__(self, mode="ai", controller=None):
        super().__init__()
        self._mode = mode
        self.controller = controller
        self.board_logic = BoardLogic()
        self.ai_agent = AIAgent('L')
        self.current_player = 'G'
        self.selected_tile = None
        self.valid_moves = []
        self.move_count = 0
        self.game_over = False
        
        self.seconds_elapsed = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_time)

        self.setWindowTitle("ល្បែងរែក - Rek Strategic Game")
        self.resize(1350, 820)
        self.init_ui()
        self.restart_game()
    def load_game(self):
        try:
            with open("savegame.json", "r", encoding="utf-8") as f:
                data = json.load(f)

            self.board_logic.grid = data["board"]
            self.current_player = data["current_player"]
            self.move_count = data["move_count"]
            self.seconds_elapsed = data["seconds_elapsed"]
            self._mode = data["mode"]

            self.lbl_moves.setText(
                f"⟳ ចលនា : {self.move_count}"
            )

            self.lbl_turn_en.setText(
                f"TURN : {'GREEN' if self.current_player == 'G' else 'LIGHT GREEN'}"
            )

            self.refresh_board_visuals()

        except FileNotFoundError:
            pass
    def save_game(self):
        data = {
            "board": self.board_logic.grid,
            "current_player": self.current_player,
            "move_count": self.move_count,
            "seconds_elapsed": self.seconds_elapsed,
            "mode": self._mode
        }

        try:
            with open("savegame.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            dlg = SaveSuccessDialog()
            dlg.exec()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Save Failed:\n{e}"
            )
    def _show_information(self):
        dlg = InformationDialog()
        dlg.exec()
    def get_valid_moves(self, r, c):
        moves = []

        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            for step in range(1, 8):
                nr = r + dr * step
                nc = c + dc * step

                if not (0 <= nr < 8 and 0 <= nc < 8):
                    break

                if self.board_logic.is_valid_move(
                    r, c, nr, nc, self.current_player
                ):
                    moves.append((nr, nc))
                else:
                    break

        return moves
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        self.setStyleSheet(f"background-color: {BG_DARK};")
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # LEFT SIDEBAR
        left_sidebar = QFrame()
        left_sidebar.setFixedWidth(240)
        left_sidebar.setStyleSheet(f"background-color: {BG_PANEL}; border: 2px solid {GOLD_BORDER}; border-radius: 18px;")
        left_layout = QVBoxLayout(left_sidebar)
        left_layout.setContentsMargins(15, 25, 15, 25)
        left_layout.setSpacing(12)

        header_title = QLabel("ល្បែងរែក\nREK GAME")
        header_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_title.setStyleSheet("color: #ca8b47; font-size: 24px; font-family: 'Khmer OS Muol Light'; line-height: 40px; border-bottom: 2px solid #6a4b18; padding-bottom: 15px;")
        left_layout.addWidget(header_title)

        self.btn_home = self._create_side_btn("ទំព័រដើម\nHOME")
        self.btn_play = self._create_side_btn("លេងហ្គេម\nPLAY GAME", active=True)
        self.btn_rules = self._create_side_btn("ច្បាប់លេង\nRULES")
        self.btn_info = self._create_side_btn("ព័ត៌មាន\nINFORMATION")
        self.btn_exit_side = self._create_side_btn("ចាកចេញ\nEXIT")

        self.btn_home.clicked.connect(self._back_home)
        self.btn_rules.clicked.connect(self._go_rules)
        self.btn_exit_side.clicked.connect(self.close)
        self.btn_info.clicked.connect(self._show_information)
        left_layout.addWidget(self.btn_home)
        left_layout.addWidget(self.btn_play)
        left_layout.addWidget(self.btn_rules)
        left_layout.addWidget(self.btn_info)
        left_layout.addStretch()
        left_layout.addWidget(self.btn_exit_side)
        main_layout.addWidget(left_sidebar)

        # CENTER CONTENT
        center_section = QWidget()
        center_layout = QVBoxLayout(center_section)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(15)

        top_bar_layout = QHBoxLayout()
        top_bar_layout.setSpacing(15)

        green_box = QFrame()
        green_box.setStyleSheet(f"background-color: #553a1a; border: 2px solid {GOLD_BORDER}; border-radius: 15px;")
        green_box.setFixedHeight(75)
        gb_layout = QHBoxLayout(green_box)
        g_dot = QLabel()
        g_dot.setFixedSize(26, 26)
        g_dot.setStyleSheet("background-color: #009a49; border-radius: 13px; border: 1px solid white;")
        g_text = QLabel("អ្នក\nGreen (You)")
        g_text.setStyleSheet("color: #f7e6c4; font-size: 13px; font-weight: bold;")
        self.lbl_score_g = QLabel("15")
        self.lbl_score_g.setStyleSheet("background-color: #110903; color: white; font-size: 16px; font-weight: bold; border-radius: 6px; padding: 5px 12px;")
        gb_layout.addWidget(g_dot)
        gb_layout.addWidget(g_text)
        gb_layout.addWidget(self.lbl_score_g)

        turn_box = QFrame()
        turn_box.setStyleSheet("background-color: #110903; border: 2px solid #6a4b18; border-radius: 15px;")
        turn_box.setFixedWidth(350)
        tb_layout = QVBoxLayout(turn_box)
        tb_layout.setContentsMargins(5, 5, 5, 5)
        tb_title = QLabel("វេន៖ អ្នក")
        tb_title.setFont(QFont("Khmer OS Muol Light", 12))
        tb_title.setStyleSheet("color: #ca8b47; border: none;")
        tb_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_turn_en = QLabel("TURN : GREEN")
        self.lbl_turn_en.setStyleSheet("color: white; font-size: 13px; font-weight: bold; border: none;")
        self.lbl_turn_en.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tb_layout.addWidget(tb_title)
        tb_layout.addWidget(self.lbl_turn_en)

        light_box = QFrame()
        light_box.setStyleSheet(f"background-color: #553a1a; border: 2px solid {GOLD_BORDER}; border-radius: 15px;")
        light_box.setFixedHeight(75)
        lb_layout = QHBoxLayout(light_box)
        l_dot = QLabel()
        l_dot.setFixedSize(26, 26)
        l_dot.setStyleSheet("background-color: #b4cc33; border-radius: 13px; border: 1px solid white;")
        l_text = QLabel("ពណ៌បៃតងភ្លឺ\nLight Green")
        l_text.setStyleSheet("color: #f7e6c4; font-size: 13px; font-weight: bold;")
        self.lbl_score_l = QLabel("15")
        self.lbl_score_l.setStyleSheet("background-color: #110903; color: white; font-size: 16px; font-weight: bold; border-radius: 6px; padding: 5px 12px;")
        lb_layout.addWidget(l_dot)
        lb_layout.addWidget(l_text)
        lb_layout.addWidget(self.lbl_score_l)

        top_bar_layout.addWidget(green_box, 1)
        top_bar_layout.addWidget(turn_box)
        top_bar_layout.addWidget(light_box, 1)
        center_layout.addLayout(top_bar_layout)

        board_container = QFrame()
        board_container.setStyleSheet(f"background-color: {BG_BOARD_CONTAINER}; border: 3px solid {GOLD_BORDER}; border-radius: 20px;")
        board_inside = QVBoxLayout(board_container)
        self.board_widget = BoardWidget()
        self.board_widget.square_clicked.connect(self.on_cell_clicked)
        board_inside.addWidget(self.board_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(board_container, 1)
        
        main_layout.addWidget(center_section, 1)

        # RIGHT SIDEBAR
        right_sidebar = QFrame()
        right_sidebar.setFixedWidth(250)
        right_sidebar.setStyleSheet(f"background-color: {BG_PANEL}; border: 2px solid {GOLD_BORDER}; border-radius: 18px;")
        right_layout = QVBoxLayout(right_sidebar)
        right_layout.setContentsMargins(15, 20, 15, 20)
        right_layout.setSpacing(12)

        info_header = QLabel("ព័ត៌មានហ្គេម\nGAME INFO")
        info_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_header.setStyleSheet("color: #ca8b47; font-family: 'Khmer OS Muol Light'; font-size: 16px; border-bottom: 1px solid #6a4b18; padding-bottom: 8px;")
        right_layout.addWidget(info_header)

        self.lbl_time = self._create_info_label("⏱️ រយៈពេល : 00:00:00")
        self.lbl_moves = self._create_info_label("⟳ ចលនា : 0")
        self.lbl_mode = self._create_info_label(f"🤖 Mode : {self._mode.upper()}")
        
        right_layout.addWidget(self.lbl_time)
        right_layout.addWidget(self.lbl_moves)
        right_layout.addWidget(self.lbl_mode)

        ctrl_header = QLabel("បញ្ជា-CONTROLS")
        ctrl_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ctrl_header.setStyleSheet("color: #ca8b47; font-family: 'Khmer OS Muol Light'; font-size: 15px; margin-top: 10px;")
        right_layout.addWidget(ctrl_header)

        btn_restart = self._create_ctrl_btn("ចាប់ផ្តើមឡើងវិញ\nRESTART", "#009a63")
        btn_undo = self._create_ctrl_btn("ត្រឡប់ក្រោយ\nUNDO MOVE", "#d47a00")
        btn_save = self._create_ctrl_btn("រក្សាទុក\nSAVE GAME", "#1d62e0")
        btn_exit_game = self._create_ctrl_btn("ចាកចេញ\nEXIT GAME", "#c81e1e")

        btn_restart.clicked.connect(self.restart_game)
        btn_undo.clicked.connect(self.undo_move)
        btn_exit_game.clicked.connect(self._back_home)
        btn_save.clicked.connect(self.save_game)

        right_layout.addWidget(btn_restart)
        right_layout.addWidget(btn_undo)
        right_layout.addWidget(btn_save)
        right_layout.addWidget(btn_exit_game)
        
        main_layout.addWidget(right_sidebar)

    def _create_side_btn(self, text, active=False):
        btn = QPushButton(text)
        btn.setFixedHeight(58)
        bg = "#381c06" if active else "transparent"
        btn.setStyleSheet(f"QPushButton {{ background-color: {bg}; color: #ca8b47; border: 1px solid {GOLD_BORDER}; border-radius: 10px; font-size: 12px; font-weight: bold; text-align: center; }} QPushButton:hover {{ background-color: #241204; color: white; }}")
        return btn

    def _create_info_label(self, text):
        lbl = QLabel(text)
        lbl.setFixedHeight(35)
        lbl.setStyleSheet("background-color: #f6e4c3; color: #110903; border-radius: 8px; padding-left: 10px; font-size: 12px; font-weight: bold;")
        return lbl

    def _create_ctrl_btn(self, text, color):
        btn = QPushButton(text)
        btn.setFixedHeight(50)
        btn.setStyleSheet(f"QPushButton {{ background-color: {color}; color: white; border-radius: 10px; font-size: 11px; font-weight: bold; text-align: center; }} QPushButton:hover {{ opacity: 0.85; }}")
        return btn

    def _update_time(self):
        self.seconds_elapsed += 1
        h = self.seconds_elapsed // 3600
        m = (self.seconds_elapsed % 3600) // 60
        s = self.seconds_elapsed % 60
        self.lbl_time.setText(f"⏱️ រយៈពេល : {h:02d}:{m:02d}:{s:02d}")

    def on_cell_clicked(self, r, c):
        if self.game_over:
            return

        piece = self.board_logic.get_piece(r, c)

        # គ្មាន piece ជ្រើស
        if self.selected_tile is None:

            if piece and piece.startswith(self.current_player):
                self.selected_tile = (r, c)
                self.valid_moves = self.get_valid_moves(r, c)
                self.refresh_board_visuals()

            return

        # មាន piece ជ្រើសរួច
        sr, sc = self.selected_tile

        # ប្តូរទៅជ្រើស piece ផ្សេង
        if piece and piece.startswith(self.current_player):
            self.selected_tile = (r, c)
            self.valid_moves = self.get_valid_moves(r, c)
            self.refresh_board_visuals()
            return

        # Move
        if (r, c) in self.valid_moves:

            self.board_logic.save_state()

            self.board_logic.make_move(
                sr, sc,
                r, c
            )

            self.move_count += 1
            self.lbl_moves.setText(
                f"⟳ ចលនា : {self.move_count}"
            )

            self.selected_tile = None
            self.valid_moves = []

            self.refresh_board_visuals()

            if self.check_game_status():
                return

            self.switch_turn()

        else:
            # click កន្លែងមិនត្រឹមត្រូវ
            self.selected_tile = None
            self.valid_moves = []
            self.refresh_board_visuals()

    def switch_turn(self):
        if self._mode == "ai":
            self.current_player = 'L'
            self.lbl_turn_en.setText("TURN : LIGHT GREEN")
            if not self.game_over:
                QApplication.processEvents()
                QTimer.singleShot(600, self._trigger_ai_move)
        else:
            self.current_player = 'L' if self.current_player == 'G' else 'G'
            self.lbl_turn_en.setText(f"TURN : {'GREEN' if self.current_player == 'G' else 'LIGHT GREEN'}")

    def _trigger_ai_move(self):
        ai_move = self.ai_agent.calculate_move(self.board_logic)
        if ai_move:
            (ai_sr, ai_sc), (ai_er, ai_ec) = ai_move
            self.board_logic.make_move(ai_sr, ai_sc, ai_er, ai_ec)
            self.move_count += 1
            self.lbl_moves.setText(f"⟳ ចលនា : {self.move_count}")
        self.refresh_board_visuals()
        if self.check_game_status(): return
        self.current_player = 'G'
        self.lbl_turn_en.setText("TURN : GREEN")

    def undo_move(self):
        if self.board_logic.undo():
            if self._mode == "ai":
                self.board_logic.undo()
                self.move_count = max(0, self.move_count - 2)
            else:
                self.move_count = max(0, self.move_count - 1)
            self.lbl_moves.setText(f"⟳ ចលនា : {self.move_count}")
            self.current_player = 'G'
            self.lbl_turn_en.setText("TURN : GREEN")
            self.refresh_board_visuals()

    def refresh_board_visuals(self):
        g_count, l_count, g_king, l_king = self.board_logic.count_pieces()
        self.lbl_score_g.setText(str(g_count))
        self.lbl_score_l.setText(str(l_count))
        for (r, c), cell in self.board_widget.cells.items():
            bg = BOARD_LIGHT if (r + c) % 2 == 0 else BOARD_DARK

            if (r, c) in self.valid_moves:
              bg = "#f7d774"   # yellow highlight

            cell.setStyleSheet(
        f"background-color:{bg}; border-radius:12px;"
    )
            while cell.layout().count():
                child = cell.layout().takeAt(0)
                if child.widget(): child.widget().deleteLater()
            piece_code = self.board_logic.get_piece(r, c)
            if piece_code:
                is_king = 'K' in piece_code
                p_color = "green" if piece_code.startswith('G') else "light"
                is_sel = (self.selected_tile == (r, c))
                cell.layout().addWidget(Piece(p_color, is_king, is_sel))

    def check_game_status(self):
        g_count, l_count, g_king, l_king = self.board_logic.count_pieces()
        winner = None
        if not g_king or g_count == 0: winner = "ក្រុមបៃតងខ្ចី (AI/Sok) ឈ្នះ!"
        elif not l_king or l_count == 0: winner = "ក្រុមបៃតង (អ្នក) ឈ្នះ!"
        if winner:
            self.game_over = True
            self.timer.stop()
            dlg = WinnerDialog(winner)
            dlg.exec()
            return True
        return False

    def restart_game(self):
        self.board_logic.reset_board()
        self.current_player = 'G'
        self.selected_tile = None
        self.valid_moves = []
        self.move_count = 0
        self.game_over = False
        self.seconds_elapsed = 0
        self.lbl_moves.setText("⟳ ចលនា : 0")
        self.lbl_turn_en.setText("TURN : GREEN")
        self.timer.start(1000)
        self.refresh_board_visuals()

    def _back_home(self):
        self.timer.stop()

        if self.controller:
            self.controller.show_home()

        self.hide()

    def _go_rules(self):
        self.timer.stop()

        if self.controller:
            self.controller.show_rules("game")

# ==========================================
# ៨. ផ្ទាំងទំព័រដើម (HOME UI)
# ==========================================
class HomeUI(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("Rèk — ល្បែងរែកខ្មែរ")
        self.resize(1100, 750)
        self.init_ui()

    def init_ui(self):
        
        self.setStyleSheet("background-color: #794c1d;")
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        left_panel = QFrame()
        left_panel.setStyleSheet("background-color: #b06c24; border: none;")
        left_panel.setFixedWidth(440)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(40, 60, 40, 60)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        deco_label = QLabel("✦  ✧  ◆  ✧  ✦")
        deco_label.setStyleSheet("color: #ecc06a; font-size: 16px;")
        logo_title = QLabel("រែក")
        logo_title.setStyleSheet("color: #ecc06a; font-size: 70px; font-family: 'Khmer OS Muol Light'; margin-top: 20px;")
        logo_sub = QLabel("R  È  K")
        logo_sub.setStyleSheet("color: #ecc06a; font-size: 20px; font-weight: bold; letter-spacing: 5px;")

        left_layout.addStretch()
        left_layout.addWidget(deco_label, alignment=Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(logo_title, alignment=Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(logo_sub, alignment=Qt.AlignmentFlag.AlignCenter)
        left_layout.addStretch()

        right_panel = QFrame()
        right_panel.setStyleSheet("""
QFrame{
    background-image: url(images/image.png);
    background-position: center;
    background-repeat: no-repeat;
    background-color: #ca8b47 ;
}
""")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(100, 200, 100, 100)
        

        self.btn_ai = self._create_menu_btn("⚔️   លេងជាមួយបញ្ញាសិប្បនិម្មិត (Play vs AI)", "#9f672b")
        self.btn_player = self._create_menu_btn("👥   លេងគ្នាពីរនាក់ (Player vs Player)", "#9f672b")
        self.btn_rules = self._create_menu_btn("📜   ច្បាប់លេងហ្គេម (Rules)", "#9f672b")
        self.btn_exit = self._create_menu_btn("✕   ចាកចេញ (Exit)", "#9f672b")

        self.btn_ai.clicked.connect(self.show_ai_dialog)
        self.btn_player.clicked.connect(lambda: self.controller.start_game("player"))
        self.btn_rules.clicked.connect(lambda: self.controller.show_rules("home"))
        self.btn_exit.clicked.connect(self.close)

        right_layout.addWidget(self.btn_ai)
        right_layout.addSpacing(30)
        right_layout.addWidget(self.btn_player)
        right_layout.addSpacing(30)
        right_layout.addWidget(self.btn_rules)
        right_layout.addSpacing(30)
        right_layout.addWidget(self.btn_exit)
        right_layout.addStretch()
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, 1)

    def _create_menu_btn(self, text, bg_color):
        btn = QPushButton(text)
        btn.setFixedHeight(55)
        btn.setFixedWidth(540)
        btn.setStyleSheet(f"QPushButton {{ background-color: {bg_color}; color: #ecc06a; border: 1px solid {GOLD_BORDER}; border-radius: 12px; font-size: 15px; text-align: left; padding-left: 25px; }} QPushButton:hover {{ background-color: #2e261d; border: 2px solid #ecc06a; }}")
        return btn
    def play_ai(self):
        dlg = NewContinueDialog()

        if dlg.exec():

            if dlg.choice == "new":
                self.controller.start_game(
                    "ai",
                    load_saved=False
                )

            elif dlg.choice == "continue":
                self.controller.start_game(
                    "ai",
                    load_saved=True
                )
    def show_ai_dialog(self):
        dlg = NewContinueDialog()

        if dlg.exec():

            if dlg.choice == "new":
                self.controller.start_game(
                    "ai",
                    load_saved=False
                )

            elif dlg.choice == "continue":
                self.controller.start_game(
                    "ai",
                    load_saved=True
                )

# ==========================================
# ៩. អ្នកគ្រប់គ្រងកម្មវិធី (CONTROLLER & MAIN)
# ==========================================
class GameController:
    def __init__(self):
        self.home_window = HomeUI(self)
        self.game_window = None
        self.rules_window = None
    def resume_game(self):
        if self.game_window:
            self.game_window.show()
            self.game_window.timer.start(1000)

        if self.rules_window:
            self.rules_window.close()
    def show_home(self): 
        self.home_window.show()

    def start_game(self, mode, load_saved=False):

        self.game_window = RekGameUI(
            mode=mode,
            controller=self
        )

        if load_saved:
            self.game_window.load_game()

        self.game_window.show()
        self.home_window.hide()

    def show_rules(self, source="home"):
        self.rules_window = RulesUI(
            controller=self,
            source=source
        )
        self.rules_window.show()

        if source == "home":
            self.home_window.hide()
        else:
            self.game_window.hide()
class WinnerDialog(QDialog):
    def __init__(self, winner):
        super().__init__()

        self.setWindowTitle("Winner")
        self.setFixedSize(420, 250)

        self.setStyleSheet("""
            QDialog{
                background:#110903;
                border:3px solid #ca8b47;
                border-radius:20px;
            }
        """)

        layout = QVBoxLayout(self)

        trophy = QLabel("🏆")
        trophy.setAlignment(Qt.AlignmentFlag.AlignCenter)
        trophy.setStyleSheet("font-size:60px;")

        title = QLabel("YOU WIN!")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            color:#ca8b47;
            font-size:28px;
            font-weight:bold;
        """)

        text = QLabel(winner)
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text.setStyleSheet("""
            color:white;
            font-size:16px;
        """)

        btn = QPushButton("OK")
        btn.setFixedHeight(45)
        btn.clicked.connect(self.accept)

        btn.setStyleSheet("""
            QPushButton{
                background:#009a49;
                color:white;
                border:none;
                border-radius:10px;
                font-size:16px;
                font-weight:bold;
            }

            QPushButton:hover{
                background:#00b85a;
            }
        """)

        layout.addStretch()
        layout.addWidget(trophy)
        layout.addWidget(title)
        layout.addWidget(text)
        layout.addStretch()
        layout.addWidget(btn)
##UI for Continue
class NewContinueDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.choice = None

        self.setWindowTitle("Play vs AI")
        self.setFixedSize(350, 180)

        layout = QVBoxLayout(self)

        title = QLabel("ជ្រើសរើសរបៀបលេង")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_new = QPushButton("New Game")
        btn_continue = QPushButton("Continue Game")

        btn_new.clicked.connect(self.new_game)
        btn_continue.clicked.connect(self.continue_game)

        layout.addWidget(title)
        layout.addWidget(btn_new)
        layout.addWidget(btn_continue)

    def new_game(self):
        self.choice = "new"
        self.accept()

    def continue_game(self):
        self.choice = "continue"
        self.accept()
class SaveSuccessDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("រក្សាទុក")
        self.setFixedSize(450, 260)

        self.setStyleSheet("""
            QDialog{
                background-color:#110903;
                border:3px solid #ca8b47;
                border-radius:20px;
            }

            QLabel{
                color:#f7e6c4;
                background:transparent;
            }

            QPushButton{
                background-color:#ca8b47;
                color:#110903;
                border:none;
                border-radius:10px;
                font-size:14px;
                font-weight:bold;
                padding:10px;
            }

            QPushButton:hover{
                background-color:#e0a95d;
            }
        """)

        layout = QVBoxLayout(self)

        icon = QLabel("💾")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size:60px;")

        title = QLabel("រក្សាទុកបានជោគជ័យ")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            color:#ca8b47;
            font-size:24px;
            font-family:'Khmer OS Muol Light';
        """)

        msg = QLabel(
            "ទិន្នន័យហ្គេមត្រូវបានរក្សាទុក\nដោយជោគជ័យ។"
        )
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet("font-size:15px;")

        btn = QPushButton("យល់ព្រម")
        btn.setFixedHeight(45)
        btn.clicked.connect(self.accept)

        layout.addStretch()
        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(msg)
        layout.addStretch()
        layout.addWidget(btn)
##Btn New Game or Continous Game
class NewContinueDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.choice = None

        self.setWindowTitle("ល្បែងរែក")
        self.setFixedSize(500, 400)

        self.setStyleSheet("""
            QDialog{
                background-color:#110903;
                border:3px solid #ca8b47;
                border-radius:20px;
            }

            QLabel{
                color:#f7e6c4;
                background:transparent;
            }

            QPushButton{
                border-radius:12px;
                
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25,25,25,25)
        layout.setSpacing(15)

        title = QLabel("ល្បែងរែក")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            color:#ca8b47;
            font-size:28px;
            font-family:'Khmer OS Muol Light';
        """)

        subtitle = QLabel("ជ្រើសរើសរបៀបលេង")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("""
            font-size:15px;
            color:#f7e6c4;
        """)

        btn_new = QPushButton(
            "🎮 ហ្គេមថ្មី"
        )
        btn_new.setFixedHeight(75)
        btn_new.setStyleSheet("""
            QPushButton{
                background:#009a49;
                color:white;
                font-size:14px;
                font-family:'Khmer OS Muol Light';
            }
            QPushButton:hover{
                background:#00b85a;
                border:2px solid #ca8b47;
            }
        """)

        btn_continue = QPushButton(
            "💾  បន្តហ្គេម"
        )
        btn_continue.setFixedHeight(75)
        btn_continue.setStyleSheet("""
            QPushButton{
                background:#1d62e0;
                color:white;
                font-size:14px;
                font-family:'Khmer OS Muol Light';
            }
            QPushButton:hover{
                background:#3578f6;
                border:2px solid #ca8b47;
            }
        """)

        btn_cancel = QPushButton("បោះបង់")
        btn_cancel.setFixedHeight(45)
        btn_cancel.setStyleSheet("""
            QPushButton{
                background:#381c06;
                color:#ca8b47;
                border:1px solid #6a4b18;
                font-family:'Khmer OS Muol Light';
            }

            QPushButton:hover{
                background:#4d2608;
            }
        """)

        btn_new.clicked.connect(self.new_game)
        btn_continue.clicked.connect(self.continue_game)
        btn_cancel.clicked.connect(self.reject)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(10)
        layout.addWidget(btn_new)
        layout.addWidget(btn_continue)
        layout.addStretch()
        layout.addWidget(btn_cancel)

    def new_game(self):
        self.choice = "new"
        self.accept()

    def continue_game(self):
        self.choice = "continue"
        self.accept()
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Khmer OS Battambang", 10))
    controller = GameController()
    controller.show_home()
    sys.exit(app.exec())