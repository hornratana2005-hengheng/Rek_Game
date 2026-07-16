import sys
import os
import copy
import json
import time
from Dashboard.database import *
from Dashboard.ui_dialogs import EnterNameDialog
from Dashboard.player_manager import save_player_name, load_player_name, clear_player_name
import random
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, 
                             QPushButton, QFrame, QVBoxLayout, QHBoxLayout, 
                             QGridLayout, QMessageBox, QTextEdit, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QLineEdit, QGraphicsDropShadowEffect, QCheckBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QVariantAnimation, QUrl, QPoint
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont,QPixmap
from PyQt6.QtWidgets import QDialog
# ==========================================
# ១. ការកំណត់ THEME & COLOR
# ==========================================
# =========================
# BACKGROUND
# =========================
BG_DARK = "#5B2C02"              # Main window
BG_PANEL = "#311604"             # Side panels
BG_BOARD_CONTAINER = "#612F08"   # Board background

# =========================
# BORDER
# =========================
GOLD_BORDER = "#9B6A24"          # Brighter bronze
SEPARATOR = "#5A4425"

# =========================
# BOARD
# =========================
BOARD_LIGHT = "#C48135"
BOARD_DARK = "#934F0F"

# =========================
# TEXT
# =========================
TEXT_LIGHT = "#F4E5C3"           # Easier to read
TEXT_MUTED = "#D5B17A"

ACCENT = "#C98B2E"

# =========================
# BUTTONS
# =========================
BUTTON_BG = "#3D210D"
BUTTON_BG_HOVER = "#5A3212"

BUTTON_SUCCESS = "#11B56A"
BUTTON_WARNING = "#E28A00"
BUTTON_INFO = "#2E6FE4"
BUTTON_DANGER = "#D92B2B"

# =========================
# CARD
# =========================
CARD_BG = "#FFF5DE"              # Cream like the timer panel
CARD_TEXT = "#231408"

# =========================
# PIECES
# =========================
PIECE_GREEN = "#16B86C"
PIECE_GREEN_BORDER = "#FFFFFF"

PIECE_LIGHT = "#C6E34A"
PIECE_LIGHT_BORDER = "#FEFFFB"

# =========================
# FONT
# =========================
FONT_KHMER = "Khmer OS SiemReap"

# Feature toggles (can be changed via Settings)
ENABLE_WIN_SOUND = True
ENABLE_WIN_ANIM = True
ENABLE_CLEAN_UI = True

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

        layout_rows = [
            "ooooooo-",
            "-------O",
            "oooooooo",
            "--------",
            "--------",
            "oooooooo",
            "O-------",
            "-ooooooo",
        ]

        for r, row in enumerate(layout_rows):
            for c, cell in enumerate(row):
                if cell == 'o':
                    if r < 3:
                        self.grid[r][c] = 'L'
                    elif r > 4:
                        self.grid[r][c] = 'G'
                elif cell == 'O':
                    if r < 3:
                        self.grid[r][c] = 'LK'
                    elif r > 4:
                        self.grid[r][c] = 'GK'

        # The top side now represents the opposing player (AI or Player 2),
        # while the bottom side is the human player's side.

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
        self.opponent_prefix = 'G' if player_prefix == 'L' else 'L'

    def calculate_move(self, board_logic):
        valid_moves = self._get_valid_moves(board_logic, self.player_prefix)
        if not valid_moves:
            return None

        best_move = random.choice(valid_moves)
        best_capture_score = -1

        for move in valid_moves:
            capture_score = self._count_captures(board_logic, move)
            if capture_score > best_capture_score:
                best_capture_score = capture_score
                best_move = move

        if best_capture_score >= 2:
            return best_move

        piece_count = sum(1 for row in board_logic.grid for piece in row if piece)
        max_depth = 4 if piece_count > 18 else 5
        # Limit AI thinking time to 1 second for responsiveness
        deadline = time.perf_counter() + 0.5

        for depth in range(2, max_depth + 1):
            if time.perf_counter() >= deadline:
                break
            _, searched_move = self._search_root(board_logic, valid_moves, depth, deadline)
            if searched_move is not None:
                best_move = searched_move
            if self._is_terminal(board_logic):
                break

        return best_move

    def _get_valid_moves(self, board_logic, player):
        valid_moves = []
        for r in range(8):
            for c in range(8):
                piece = board_logic.get_piece(r, c)
                if piece and piece.startswith(player):
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        for step in range(1, 8):
                            nr, nc = r + dr * step, c + dc * step
                            if 0 <= nr < 8 and 0 <= nc < 8:
                                if board_logic.is_valid_move(r, c, nr, nc, player):
                                    valid_moves.append(((r, c), (nr, nc)))
                                else:
                                    break
                            else:
                                break
        return valid_moves

    def _count_captures(self, board_logic, move):
        sr, sc = move[0]
        er, ec = move[1]
        temp_board = copy.deepcopy(board_logic)
        captured = temp_board.make_move(sr, sc, er, ec)
        return len(captured)

    def _is_terminal(self, board_logic):
        g_count, l_count, g_king, l_king = board_logic.count_pieces()
        return not g_king or g_count == 0 or not l_king or l_count == 0

    def _evaluate_board(self, board_logic):
        g_count, l_count, g_king, l_king = board_logic.count_pieces()
        if not l_king or l_count == 0:
            return 100000
        if not g_king or g_count == 0:
            return -100000

        my_count = l_count if self.player_prefix == 'L' else g_count
        opp_count = g_count if self.player_prefix == 'L' else l_count
        my_king = l_king if self.player_prefix == 'L' else g_king
        opp_king = g_king if self.player_prefix == 'L' else l_king

        score = (my_count - opp_count) * 14
        score += (1 if my_king else 0) * 30
        score -= (1 if opp_king else 0) * 30

        score += self._mobility_score(board_logic, self.player_prefix) * 4
        score -= self._mobility_score(board_logic, self.opponent_prefix) * 4

        score += self._position_score(board_logic, self.player_prefix) * 2
        score -= self._position_score(board_logic, self.opponent_prefix) * 2

        return score

    def _mobility_score(self, board_logic, player):
        return len(self._get_valid_moves(board_logic, player))

    def _position_score(self, board_logic, player):
        center_weights = {
            (3, 3): 4, (3, 4): 4, (4, 3): 4, (4, 4): 5,
            (2, 3): 2, (3, 2): 2, (4, 5): 2, (5, 4): 2,
            (2, 4): 2, (4, 2): 2, (3, 5): 2, (5, 3): 2,
        }
        score = 0
        for r in range(8):
            for c in range(8):
                piece = board_logic.get_piece(r, c)
                if piece and piece.startswith(player):
                    score += center_weights.get((r, c), 0)
                    if 'K' in piece:
                        score += 2
        return score

    def _search_root(self, board_logic, valid_moves, depth, deadline):
        best_score = -10**9
        best_move = valid_moves[0]
        for move in valid_moves:
            if time.perf_counter() >= deadline:
                break
            (sr, sc), (er, ec) = move
            child_board = copy.deepcopy(board_logic)
            child_board.make_move(sr, sc, er, ec)
            score, _ = self._minimax(child_board, depth - 1, -10**9, 10**9, False, deadline)
            if score > best_score:
                best_score = score
                best_move = move
        return best_score, best_move

    def _minimax(self, board_logic, depth, alpha, beta, maximizing, deadline):
        if time.perf_counter() >= deadline:
            return self._evaluate_board(board_logic), None
        if depth == 0 or self._is_terminal(board_logic):
            return self._evaluate_board(board_logic), None

        player = self.player_prefix if maximizing else self.opponent_prefix
        moves = self._get_valid_moves(board_logic, player)
        if not moves:
            return self._evaluate_board(board_logic), None

        if maximizing:
            best_score = -10**9
            best_move = moves[0]
            for move in moves:
                if time.perf_counter() >= deadline:
                    break
                (sr, sc), (er, ec) = move
                child_board = copy.deepcopy(board_logic)
                child_board.make_move(sr, sc, er, ec)
                score, _ = self._minimax(child_board, depth - 1, alpha, beta, False, deadline)
                if score > best_score:
                    best_score = score
                    best_move = move
                alpha = max(alpha, best_score)
                if beta <= alpha:
                    break
            return best_score, best_move

        best_score = 10**9
        best_move = moves[0]
        for move in moves:
            if time.perf_counter() >= deadline:
                break
            (sr, sc), (er, ec) = move
            child_board = copy.deepcopy(board_logic)
            child_board.make_move(sr, sc, er, ec)
            score, _ = self._minimax(child_board, depth - 1, alpha, beta, True, deadline)
            if score < best_score:
                best_score = score
                best_move = move
            beta = min(beta, best_score)
            if beta <= alpha:
                break
        return best_score, best_move

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
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)
        
        for r in range(8):
            for c in range(8):
                cell = ClickableCell(r, c)
                bg = BOARD_LIGHT if (r + c) % 2 == 0 else BOARD_DARK
                cell.setStyleSheet(
                    f"background-color: {bg}; border-radius: 14px; border: 1px solid rgba(255,255,255,0.08);"
                )
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
            painter.setBrush(QBrush(QColor(255, 255, 255, 140)))
            painter.setPen(QPen(QColor(ACCENT), 2, Qt.PenStyle.SolidLine))
            painter.drawEllipse(1, 1, 46, 46)

        if self.color == "green":
            fill = QColor(PIECE_GREEN)
            border = QColor(PIECE_GREEN_BORDER)
        else:
            fill = QColor(PIECE_LIGHT)
            border = QColor(PIECE_LIGHT_BORDER)

        if self.king:
            border = QColor('white')

        painter.setBrush(QBrush(fill))
        painter.setPen(QPen(border, 2))
        painter.drawEllipse(4, 4, 40, 40)
        
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(255, 255, 255, 90), 1))
        painter.drawEllipse(8, 8, 32, 32)

        if self.king:
            painter.setPen(QPen(QColor('black'), 4))
            painter.setFont(QFont("Khmer OS Muol Light", 20))
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
        self.resize(800, 700)
        self.init_ui()
        screen = QApplication.primaryScreen().availableGeometry()
        frame = self.frameGeometry()
        frame.moveCenter(screen.center())
        self.move(frame.topLeft())

    def init_ui(self):
        self.setStyleSheet(
            f"QWidget {{ background-color: {BG_DARK}; color: {TEXT_LIGHT}; }}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("ច្បាប់លេងល្បែងរែកខ្មែរ")
        title.setStyleSheet(f"color: {TEXT_LIGHT}; font-size: 30px; font-family: 'Khmer OS Muol Light';")

        content = QTextEdit()
        content.setReadOnly(True)
        content.setStyleSheet(f"background-color: {BG_PANEL}; color: {TEXT_LIGHT}; font-size: 16px; border: 1px solid rgba(255,255,255,0.08); border-radius: 18px; padding: 18px; line-height: 30px;")
        
        rules_text = (
            "១. ការរៀបចំក្តារដំបូង៖ កូនអុកមាន ២ ពណ៌ តម្រៀបជាន់គ្នាជាពីរជួរ និង ស្តេចនៅជួរទី២ និងទី៧ តាមទម្រង់ Grid លម្អិត។\n\n"
            "២. របៀបផ្លាស់ទី (Long-Range Move)៖ កូនអុកអាចរំកិលទៅមុខ ថយក្រោយ ឆ្វេង ឬ ស្តាំ បានច្រើនក្រឡាកក្នុងពេលតែមួយ ឱ្យតែផ្លូវត្រង់នោះទំនេរគ្មានគ្រាប់បាំង។\n\n"
            "៣. ក្បួនស៊ីរែក (RÈK)៖ នៅពេលអ្នករំកិលកូនអុកទៅចំកណ្តាលចន្លោះកូនសត្រូវពីរ "
            "នោះអ្នកនឹងរែកស៊ីកូនសត្រូវទាំងពីរដាច់ចេញពីក្តារភ្លាមៗ។\n\n"
            "៤. ក្បួនឡោមព័ទ្ធ (GNYAP)៖ នៅពេលកូនអុករបស់សត្រូវត្រូវបានព័ទ្ធជុំវិញគ្រប់ច្រកល្ហក គ្មានផ្លូវរត់ចេញបាន វានឹងត្រូវងាប់ដោយស្វ័យប្រវត្តិ。\n\n"
            "៥. លក្ខខណ្ឌឈ្នះ៖ អ្នកដែលបានស៊ីស្តេច «♔» របស់សត្រូវមុន ឬស៊ីគ្រាប់សត្រូវអស់ពីក្តារ គឺជាអ្នកឈ្នះ"
        )
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        content.setPlainText(rules_text)
        layout.addWidget(content)

        btn_back = QPushButton("បិទ")
        btn_back.setFixedSize(250, 50)
        btn_back.setStyleSheet(f"QPushButton {{ background-color: {ACCENT}; color: white; border: none; border-radius: 14px; font-weight: bold; font-family: ''Khmer OS Muol Light''; }} QPushButton:hover {{ background-color: {BUTTON_BG_HOVER}; }}")
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

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {BG_DARK};
                border: 1px solid {SEPARATOR};
                border-radius: 22px;
            }}

            QLabel {{
                color: {TEXT_LIGHT};
            }}

            QTextEdit {{
                background-color: {BG_PANEL};
                color: {TEXT_LIGHT};
                border: 1px solid {SEPARATOR};
                padding: 14px;
                border-radius: 16px;
            }}

            QPushButton {{
                background-color: {ACCENT};
                color: white;
                border: none;
                border-radius: 14px;
                padding: 10px 16px;
                font-family: '{FONT_KHMER}';
            }}

            QPushButton:hover {{
                background-color: {BUTTON_BG_HOVER};
            }}
        """)

        layout = QVBoxLayout(self)

        title = QLabel("ព័ត៌មានអំពីល្បែងរែក")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-size:24px;
            font-family: 'Khmer OS Muol Light';
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
        self.ai_thinking = False
        
        self.seconds_elapsed = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_time)

        self.setWindowTitle("ល្បែងរែក - Rek Strategic Game")
        self.showFullScreen()
        self.init_ui()
        self.restart_game()
    def load_game(self):

        data = load_game_db()

        if not data:
            return

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
    def save_game(self):

        save_game_db(
            self.board_logic.grid,
            self.current_player,
            self.move_count,
            self.seconds_elapsed,
            self._mode
        )

        dlg = SaveSuccessDialog()
        dlg.exec()
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
        central.setStyleSheet(f"background-color: {BG_DARK};")
        self.setCentralWidget(central)
        self.setStyleSheet(
            f"QMainWindow {{ background-color: {BG_DARK}; }}"
        )
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # LEFT SIDEBAR
        left_sidebar = QFrame()
        left_sidebar.setFixedWidth(280)
        left_sidebar.setStyleSheet(
            f"background-color: {BG_PANEL}; border: 1px solid rgba(255,255,255,0.08); border-radius: 22px;"
        )
        left_layout = QVBoxLayout(left_sidebar)
        left_layout.setContentsMargins(20, 24, 20, 24)
        left_layout.setSpacing(14)

        header_title = QLabel("ល្បែងរែក\nREK GAME")
        header_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_title.setStyleSheet(
            f"color: {TEXT_LIGHT}; font-size: 24px; "
            "font-family: 'Khmer OS Muol Light'; "
            f"line-height: 38px; border-bottom: 1px solid rgba(255,255,255,0.08); "
            "padding-bottom: 14px;"
        )
        left_layout.addWidget(header_title)

        # ===== Player Name =====
        player_name = load_player_name() or "Player"

        self.lbl_player = QLabel(f"👤 {player_name}")
        self.lbl_player.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_player.setStyleSheet(
            f"color: {TEXT_LIGHT}; font-size: 14px; font-weight: bold; padding: 12px 10px; "
            f"background-color: {BG_BOARD_CONTAINER}; border-radius: 14px; border: 1px solid rgba(255,255,255,0.08);"
        )
        left_layout.addWidget(self.lbl_player)

        # ===== Menu Buttons =====
        self.btn_home = self._create_side_btn("ទំព័រដើម",BG_DARK, TEXT_LIGHT)
        self.btn_play = self._create_side_btn("លេងហ្គេម",BOARD_LIGHT, TEXT_LIGHT, active=True)
        self.btn_rules = self._create_side_btn("ច្បាប់លេង",BG_DARK, TEXT_LIGHT)
        self.btn_info = self._create_side_btn("ព័ត៌មាន", BG_DARK, TEXT_LIGHT)
        self.btn_exit_side = self._create_side_btn("បិទកម្មវិធី",'red', 'white')
    
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
        green_box.setStyleSheet(
            f"background-color: {BOARD_LIGHT}; border: 1px solid rgba(255,255,255,0.08); border-radius: 18px;"
        )
        green_box.setFixedHeight(80)
        gb_layout = QHBoxLayout(green_box)
        g_dot = QLabel()
        g_dot.setFixedSize(28, 28)
        g_dot.setStyleSheet(
            f"background-color: {PIECE_GREEN}; border-radius: 14px; border: 1px solid {SEPARATOR};"
        )
        g_text = QLabel("អ្នក\nGreen (You)")
        g_text.setStyleSheet(f"color: {TEXT_LIGHT}; font-size: 13px; font-weight: bold; line-height: 18px;")
        self.lbl_score_g = QLabel("15")
        self.lbl_score_g.setStyleSheet(
            f"background-color: {BG_PANEL}; color: {TEXT_LIGHT}; font-size: 16px; font-weight: bold; border-radius: 8px; padding: 6px 14px;"
        )
        gb_layout.addWidget(g_dot)
        gb_layout.addWidget(g_text)
        gb_layout.addStretch()
        gb_layout.addWidget(self.lbl_score_g)

        turn_box = QFrame()
        turn_box.setStyleSheet(f"background-color: {BG_PANEL}; border: 1px solid rgba(255,255,255,0.08); border-radius: 15px;")
        turn_box.setFixedWidth(350)
        tb_layout = QVBoxLayout(turn_box)
        tb_layout.setContentsMargins(12, 10, 12, 10)
        self.tb_title = QLabel("វេន៖ អ្នក")
        self.tb_title.setFont(QFont("Khmer OS SiemReap", 12))
        self.tb_title.setStyleSheet(f"color: {TEXT_LIGHT}; border: none;")
        self.tb_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_turn_en = QLabel("TURN : GREEN")
        self.lbl_turn_en.setStyleSheet(f"color: {PIECE_GREEN}; font-size: 13px; font-weight: bold; border: none;")
        self.lbl_turn_en.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tb_layout.addWidget(self.tb_title)
        tb_layout.addWidget(self.lbl_turn_en)

        light_box = QFrame()
        light_box.setStyleSheet(f"background-color: {BOARD_LIGHT}; border: 1px solid rgba(255,255,255,0.08); border-radius: 15px;")
        light_box.setFixedHeight(75)
        lb_layout = QHBoxLayout(light_box)
        l_dot = QLabel()
        l_dot.setFixedSize(26, 26)
        l_dot.setStyleSheet(f"background-color: {PIECE_LIGHT}; border-radius: 13px; border: 1px solid {SEPARATOR};")
        l_text = QLabel("ពណ៌បៃតងភ្លឺ\nLight Green")
        l_text.setStyleSheet(f"color: {TEXT_LIGHT}; font-size: 13px; font-weight: bold; line-height: 18px;")
        self.lbl_score_l = QLabel("15")
        self.lbl_score_l.setStyleSheet(f"background-color: {BG_PANEL}; color: {TEXT_LIGHT}; font-size: 16px; font-weight: bold; border-radius: 8px; padding: 6px 14px;")
        lb_layout.addWidget(l_dot)
        lb_layout.addWidget(l_text)
        lb_layout.addWidget(self.lbl_score_l)

        top_bar_layout.addWidget(green_box, 1)
        top_bar_layout.addWidget(turn_box)
        top_bar_layout.addWidget(light_box, 1)
        center_layout.addLayout(top_bar_layout)

        board_container = QFrame()
        board_container.setStyleSheet(f"background-color: {BG_PANEL}; border: 1px solid rgba(255,255,255,0.08); border-radius: 20px;")
        board_inside = QVBoxLayout(board_container)
        board_inside.setContentsMargins(18, 18, 18, 18)
        self.board_widget = BoardWidget()
        self.board_widget.square_clicked.connect(self.on_cell_clicked)
        board_inside.addWidget(self.board_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(board_container, 1)
        
        main_layout.addWidget(center_section, 1)

        # RIGHT SIDEBAR
        right_sidebar = QFrame()
        right_sidebar.setFixedWidth(280)
        right_sidebar.setStyleSheet(
            f"background-color: {BG_PANEL}; border: 1px solid rgba(255,255,255,0.08); border-radius: 22px;"
        )
        right_layout = QVBoxLayout(right_sidebar)
        right_layout.setContentsMargins(18, 22, 18, 22)
        right_layout.setSpacing(14)

        info_header = QLabel("ព័ត៌មានហ្គេម\nGAME INFO")
        info_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_header.setStyleSheet(f"color: {ACCENT}; font-family: 'Khmer OS Muol Light'; font-size: 16px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 8px;")
        right_layout.addWidget(info_header)

        self.lbl_time = self._create_info_label("⏱️ រយៈពេល : 00:00:00")
        self.lbl_moves = self._create_info_label("⟳ ចលនា : 0")
        self.lbl_mode = self._create_info_label(f"🤖 Mode : {self._mode.upper()}")
        self.lbl_ai_status = self._create_info_label("🤖 AI : Your turn")
        
        right_layout.addWidget(self.lbl_time)
        right_layout.addWidget(self.lbl_moves)
        right_layout.addWidget(self.lbl_mode)
        right_layout.addWidget(self.lbl_ai_status)

        ctrl_header = QLabel("បញ្ជា-CONTROLS")
        ctrl_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ctrl_header.setStyleSheet(f"color: {ACCENT}; font-family: 'Khmer OS Muol Light'; font-size: 15px; margin-top: 10px;")
        right_layout.addWidget(ctrl_header)

        btn_restart = self._create_ctrl_btn("ចាប់ផ្តើមឡើងវិញ", BUTTON_SUCCESS)
        btn_undo = self._create_ctrl_btn("ត្រឡប់ក្រោយ", BUTTON_WARNING)
        btn_save = self._create_ctrl_btn("រក្សាទុក", BUTTON_INFO)
        btn_settings = self._create_ctrl_btn("⚙️ Settings", BUTTON_INFO)

        btn_restart.clicked.connect(self.restart_game)
        btn_undo.clicked.connect(self.undo_move)
        btn_settings.clicked.connect(self._open_settings)
        btn_save.clicked.connect(self.save_game)

        right_layout.addWidget(btn_restart)
        right_layout.addWidget(btn_undo)
        right_layout.addWidget(btn_save)
        right_layout.addWidget(btn_settings)
        
        main_layout.addWidget(right_sidebar)
    

    def _create_side_btn(self, text, bg, color, active=False):
        btn = QPushButton(text)
        btn.setFixedHeight(58)
        bg if active else BG_BOARD_CONTAINER
        color if active else TEXT_LIGHT
        hover = BUTTON_BG_HOVER
        btn.setStyleSheet(
            f"QPushButton {{font-family: 'Khmer OS Muol Light'; background-color: {bg}; color: {color}; border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; font-size: 13px; text-align: center; padding: 12px; }} "
            f"QPushButton:hover {{ background-color: #B07302; color: white; }}"
        )
        return btn

    def _create_info_label(self, text):
        lbl = QLabel(text)
        lbl.setFixedHeight(35)
        lbl.setStyleSheet(f"background-color: {CARD_BG}; color: {CARD_TEXT}; border-radius: 10px; padding-left: 14px; font-size: 13px; font-weight: bold; border: 1px solid rgba(255,255,255,0.08);")
        return lbl

    def _create_ctrl_btn(self, text, color):
        btn = QPushButton(text)
        btn.setFixedHeight(50)
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {color}; color: white; border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; font-size: 13px; font-weight: bold; font-family: ''Khmer OS Muol Light''; text-align: center; padding: 12px; }} "
            f"QPushButton:hover {{ background-color: {BUTTON_BG_HOVER}; }}"
        )
        return btn

    def _open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            # settings dialog writes globals directly
            pass

    def _update_time(self):
        self.seconds_elapsed += 1
        h = self.seconds_elapsed // 3600
        m = (self.seconds_elapsed % 3600) // 60
        s = self.seconds_elapsed % 60
        self.lbl_time.setText(f"⏱️ រយៈពេល : {h:02d}:{m:02d}:{s:02d}")

    def _set_ai_status(self, text):
        if hasattr(self, 'lbl_ai_status'):
            self.lbl_ai_status.setText(f"🤖 AI : {text}")

    def on_cell_clicked(self, r, c):
        if self.game_over or self.ai_thinking:
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
            self.tb_title.setText("វេន៖ AI")
            self.lbl_turn_en.setText("TURN : LIGHT GREEN")
            self.ai_thinking = True
            self._set_ai_status("thinking...")
            if not self.game_over:
                QApplication.processEvents()
                QTimer.singleShot(2000, self._trigger_ai_move)
        else:
            self.current_player = 'L' if self.current_player == 'G' else 'G'
            self.tb_title.setText(f"វេន៖ {'អ្នក' if self.current_player == 'G' else 'អ្នកដៃគូប្រកួត'}")
            self.lbl_turn_en.setText(f"TURN : {'GREEN' if self.current_player == 'G' else 'LIGHT GREEN'}")

    def _trigger_ai_move(self):
        self._set_ai_status("choosing a move...")
        ai_move = self.ai_agent.calculate_move(self.board_logic)
        if ai_move:
            (ai_sr, ai_sc), (ai_er, ai_ec) = ai_move
            self.board_logic.make_move(ai_sr, ai_sc, ai_er, ai_ec)
            self.move_count += 1
            self.lbl_moves.setText(f"⟳ ចលនា : {self.move_count}")
            self._set_ai_status("moved")
        else:
            self._set_ai_status("no moves")
        self.ai_thinking = False
        self.refresh_board_visuals()
        if self.check_game_status():
            return
        self.current_player = 'G'
        self.tb_title.setText("វេន៖ អ្នក")
        self.lbl_turn_en.setText("TURN : GREEN")
        self._set_ai_status("your turn")

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
                bg = ACCENT

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

        if not g_king or g_count == 0:
            winner = "AI ឈ្នះ!"
        elif not l_king or l_count == 0:
            winner = "អ្នក ឈ្នះ!"

        # 👉 IMPORTANT: only run when game ended
        if winner is None:
            return False

        player_name = load_player_name() or "Player"

        if self._mode == "ai":
            if "អ្នក" in winner:
                save_history(player_name, "AI", "WIN")
            else:
                save_history(player_name, "AI", "LOSE")

        else:
            save_history(player_name, "PVP", winner)

        # (optional) show winner dialog here if you want
        self.game_over = True
        self.timer.stop()

        dlg = WinnerDialog(winner, parent=self)
        dlg.exec()

        # If user chose to play again from the dialog, restart the game
        if hasattr(dlg, 'choice') and dlg.choice == 'play_again':
            self.restart_game()

        return True
    def restart_game(self):
        self.board_logic.reset_board()
        self.current_player = 'G'
        self.selected_tile = None
        self.valid_moves = []
        self.move_count = 0
        self.game_over = False
        self.ai_thinking = False
        self.seconds_elapsed = 0
        self.lbl_moves.setText("⟳ ចលនា : 0")
        self.lbl_turn_en.setText("TURN : GREEN")
        self._set_ai_status("your turn")
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
class LoginUI(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("Login — Rek Game")
        self.resize(1000,1000)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet(f"QWidget {{ background-color: {BG_DARK}; color: {TEXT_LIGHT}; }}")
        self.showFullScreen()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(80, 80, 80, 80)
        layout.setSpacing(20)

        card = QFrame()
        card = QFrame()
        card.setStyleSheet(f"background-color: {BG_PANEL}; border: 1px solid rgba(255,255,255,0.06); border-radius: 24px;")
        # subtle drop shadow for depth
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(28)
        shadow.setXOffset(0)
        shadow.setYOffset(6)
        shadow.setColor(QColor(0, 0, 0, 120))
        card.setGraphicsEffect(shadow)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 32, 36, 32)
        card_layout.setSpacing(12)

        title = QLabel("សូមស្វាគមន៍មកកាន់ហ្គេមរែក\nWelcome to Rèk Game")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {TEXT_LIGHT}; font-size: 28px; font-family: 'Khmer OS Muol Light';")

        subtitle = QLabel("Enter your name to continue")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 15px;")

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("បញ្ចូលឈ្មោះរបស់អ្នកនៅទីនេះ...")
        self.name_input.setFixedHeight(52)
        self.name_input.setStyleSheet(f"QLineEdit {{ background-color: {BG_DARK}; color: {TEXT_LIGHT}; border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding-left: 14px; font-size: 16px; }} QLineEdit::placeholder {{ color: {TEXT_MUTED}; }}")
        self.name_input.returnPressed.connect(self.login)
        self.name_input.textChanged.connect(self._hide_login_error)
        

        # inline error message (hidden until needed)
        self.login_error = QLabel("")
        self.login_error.setStyleSheet(f"color: {BUTTON_DANGER}; font-size: 13px; padding: 6px 8px;")
        self.login_error.setVisible(False)

        saved_name = load_player_name()
        if saved_name:
            self.name_input.setText(saved_name)

        text = QLabel("អ្នកត្រូវតែបញ្ចូលឈ្មោះរបស់អ្នកដើម្បីចូលទៅក្នុងហ្គេម")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_login = QPushButton("Login")
        btn_login.setFixedHeight(50)
        btn_login.setStyleSheet(f"QPushButton {{ background-color: green; color: white; border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; font-size: 15px; font-weight: bold; font-family: ''Khmer OS Muol Light''; }} QPushButton:hover {{ background-color: {BUTTON_BG_HOVER}; }}")
        btn_login.clicked.connect(self.login)
        btn_back = self.create_back_button()

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(8)
        card_layout.addWidget(self.name_input)
        card_layout.addWidget(self.login_error)
        card_layout.addWidget(text)
        card_layout.addSpacing(20)
        card_layout.addWidget(btn_login)
        layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)
        card_layout.addSpacing(6)
        card_layout.addWidget(btn_back,alignment=Qt.AlignmentFlag.AlignCenter)
        
    def create_back_button(self):
        btn_back = QPushButton(" បិទ ")
        btn_back.setFixedSize(400, 50)
        btn_back.setStyleSheet(f"""
            QPushButton {{
                background-color: red;
                color: white;
                border: none;
                border-radius: 14px;
                font-weight: bold;
                font-family: 'Khmer OS Muol Light';
            }}
            QPushButton:hover {{
                background-color: blue;
            }}
        """)
        btn_back.clicked.connect(self._back)
        return btn_back
    def login(self):
        name = self.name_input.text().strip()
        if not name:
            self.login_error.setText("⚠ សូមបញ្ចូលឈ្មោះរបស់អ្នក")
            self.login_error.setVisible(True)
            return

        save_player_name(name)
        self.controller.show_home()
    def _back(self):
        self.close()

    def _hide_login_error(self):
        if self.login_error.isVisible():
            self.login_error.setVisible(False)


class HomeUI(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("Rèk — ល្បែងរែកខ្មែរ")
        self.setFixedSize(1200,1200)
        self.init_ui()

    def init_ui(self):
        
        self.setStyleSheet(f"QWidget {{ background-color: {BG_DARK}; color: {TEXT_LIGHT}; }}")
        self.showFullScreen()
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        left_panel = QFrame()
        left_panel.setStyleSheet(f"background-color: {BG_PANEL}; border: none;")
        left_panel.showFullScreen()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(40, 60, 40, 60)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        deco_label = QLabel("✦  ✧  ◆  ✧  ✦")
        deco_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 16px;")
        logo_title = QLabel("រែក")
        logo_title.setStyleSheet(f"color: {TEXT_LIGHT}; font-size: 70px; font-family: 'Khmer OS Muol Light'; margin-top: 20px;")
        logo_sub = QLabel("R  È  K")
        logo_sub.setStyleSheet(f"color: {ACCENT}; font-size: 20px; font-weight: bold; letter-spacing: 5px;")
        description = QLabel("""
                <p align="center">
            
                សូមរីករាយនឹងការលេង!<br>
                យើងខ្ញុំសូមអភ័យទោសចំពោះកំហុសណាមួយ
                និងស្វាគមន៍រាល់មតិយោបល់សម្រាប់ការកែលម្អ។<br><br>

                <b>សូមអរគុណ!</b>
                </p>
                """)
        description.setWordWrap(True)
        description.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 14px; font-family: 'Khmer OS Muol Light'; margin-top: 20px; ")
        font = description.font()
        font.setLetterSpacing(font.SpacingType.AbsoluteSpacing, 2)
        description.setFont(font)
        
        left_layout.addStretch()
        left_layout.addWidget(deco_label, alignment=Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(logo_title, alignment=Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(logo_sub, alignment=Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(description, alignment=Qt.AlignmentFlag.AlignCenter)
        left_layout.addStretch()

        right_panel = QFrame()
        right_panel.showFullScreen()
        right_panel.setStyleSheet(f"QFrame{{ background-color: {BG_BOARD_CONTAINER}; border-radius: 0px; border-left: 1px solid rgba(255,255,255,0.08); }}")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(80, 120, 80, 100)
        
        text_top = QLabel("សូមស្វាគមន៍មកកាន់ ហ្គេមរែកខ្មែរ")
        text_top.setStyleSheet(f"color: rgb(245, 222, 179); font-size: 30px; font-family: 'Khmer OS Muol Light'; margin-bottom: 20px;")
        text = QLabel("សូមជ្រើសរើសរបៀបលេង និង មុខងារដែលអ្នកចង់ប្រើ")
        text.setStyleSheet(f"color: rgba(245, 222, 179, 0.5); font-size: 15px; font-family: 'Khmer OS Muol Light'; margin-bottom: 20px;")

        self.btn_ai = self._create_menu_btn("⚔️   លេងជាមួយបញ្ញាសិប្បនិម្មិត (Play vs AI)", ACCENT,'normal')
        self.btn_player = self._create_menu_btn("👥   លេងគ្នាពីរនាក់ (Player vs Player)", ACCENT, 'normal')
        self.btn_rules = self._create_menu_btn("📜   ច្បាប់លេងហ្គេម (Rules)", ACCENT, 'normal')
        self.btn_history = self._create_menu_btn("🏆 ប្រវត្តិការលេង (History)", ACCENT, 'normal')
        self.btn_exit = self._create_menu_btn("✕   បិទហ្គេម (Exit)", 'red', 'normal')
        self.btn_logout = self._create_menu_btn("⇥   ចាកចេញ​(Logout)", 'blue', 'normal')
        

        self.btn_ai.clicked.connect(self.show_ai_dialog)
        self.btn_player.clicked.connect(lambda: self.controller.start_game("player"))
        self.btn_rules.clicked.connect(lambda: self.controller.show_rules("home"))
        self.btn_logout.clicked.connect(self.logout)
        self.btn_history.clicked.connect(self.show_history)
        self.btn_exit.clicked.connect(self.close)
        
        
        right_layout.addWidget(text_top, alignment=Qt.AlignmentFlag.AlignCenter)
        right_layout.addStretch()
        right_layout.addWidget(text, alignment=Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.btn_ai, alignment=Qt.AlignmentFlag.AlignCenter)
        right_layout.addSpacing(20)
        right_layout.addWidget(self.btn_player, alignment=Qt.AlignmentFlag.AlignCenter)
        right_layout.addSpacing(20)
        right_layout.addWidget(self.btn_rules, alignment=Qt.AlignmentFlag.AlignCenter)
        right_layout.addSpacing(20)
        right_layout.addWidget(self.btn_history, alignment=Qt.AlignmentFlag.AlignCenter)
        right_layout.addSpacing(20)
        right_layout.addWidget(self.btn_logout, alignment=Qt.AlignmentFlag.AlignCenter)
        right_layout.addSpacing(20)
        right_layout.addWidget(self.btn_exit, alignment=Qt.AlignmentFlag.AlignCenter)
        right_layout.addStretch()
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, 1)
        
        
    def show_history(self):
        dlg = HistoryDialog()
        dlg.exec()


    def logout(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Logout")
        dialog.setFixedSize(350, 300)
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)

        dialog.setStyleSheet("""
            QDialog {
                background: #5B2C02;
                border-radius: 12px;
            }

            QLabel {
                color: white;
                font-size: 16px;      
            }

            QPushButton {
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                min-width: 100px;
                min-height: 40px;
            }
        """)

        label = QLabel("តើអ្នកប្រាកដថាចង់ ចាកចេញ ពីហ្គេមនេះឬ?")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        yes_btn = QPushButton("បាទ/ចាស")
        no_btn = QPushButton("ទេ")

        yes_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
            }
            QPushButton:hover {
                background-color: #219150;
            }
            QPushButton:pressed {
                background-color: #1E8449;
            }
        """)

        no_btn.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
            QPushButton:pressed {
                background-color: #A93226;
            }
        """)
        icon = QLabel("😊")
        icon.setStyleSheet("font-size: 48px;")
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(yes_btn)
        button_layout.addWidget(no_btn)
        button_layout.addStretch()

        layout = QVBoxLayout(dialog)
        layout.addStretch()
        layout.addWidget(icon, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        layout.addSpacing(30)
        layout.addLayout(button_layout)
        layout.addStretch()

        yes_btn.clicked.connect(dialog.accept)
        no_btn.clicked.connect(dialog.reject)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            clear_player_name()

            if getattr(self, "game_window", None):
                self.game_window.close()
                self.game_window = None

            # If HomeUI has a controller
            if hasattr(self, "controller"):
                self.controller.show_login()
            else:
                self.show_login()
    def _create_menu_btn(self, text, bg_color, font_weight):
        btn = QPushButton(text)
        btn.setFixedHeight(55)
        btn.setFixedWidth(540)
        btn.setStyleSheet(f"QPushButton {{ font-family: 'Khmer OS Muol Light'; background-color: {bg_color}; color: {TEXT_LIGHT}; border: 1px solid rgba(255,255,255,0.08);font-weight: {font_weight}; border-radius: 18px; font-size: 15px; text-align: left; padding-left: 25px; }} QPushButton:hover {{ background-color: {BUTTON_BG_HOVER}; border: 1px solid rgba(255,255,255,0.2); }}")
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
# ១០. អ្នកគ្រប់គ្រងកម្មវិធី (CONTROLLER & MAIN)
# ==========================================
class GameController:
    def __init__(self):
        self.login_window = LoginUI(self)
        self.home_window = HomeUI(self)
        self.game_window = None
        self.rules_window = None

    def start(self):
        if load_player_name():
            self.show_home()
        else:
            self.show_login()

    def resume_game(self):
        if self.game_window:
            self.game_window.show()
            self.game_window.timer.start(1000)

        if self.rules_window:
            self.rules_window.close()
    def show_login(self):
        if self.login_window:
            self.login_window.show()
        if self.home_window:
            self.home_window.hide()
        if self.game_window:
            self.game_window.hide()
        if self.rules_window:
            self.rules_window.hide()

    def show_home(self): 
        self.home_window.showFullScreen()
        self.home_window.raise_()
        self.home_window.activateWindow()
        
        if self.login_window:
            self.login_window.hide()
        if self.game_window:
            self.game_window.hide()
        if self.rules_window:
            self.rules_window.hide()

    # def logout(self):
    #     answer = QMessageBox.question(
    #         self.home_window,
    #         "Logout",
    #         "Do you want to log out?",
    #         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    #         QMessageBox.StandardButton.No
    #     )

    #     if answer == QMessageBox.StandardButton.Yes:
    #         clear_player_name()
    #         if self.game_window:
    #             self.game_window.close()
    #             self.game_window = None
    #         self.show_login()

    def start_game(self, mode, load_saved=False):

        if mode == "ai" and not load_saved:
            saved_name = load_player_name()
            if saved_name:
                save_player_name(saved_name)
            else:
                dialog = EnterNameDialog()

                if dialog.exec() == 0:
                    return

                saved_name = dialog.get_name()

                if saved_name:
                    save_player_name(saved_name)

        self.game_window = RekGameUI(
            mode=mode,
            controller=self
        )

        # Load saved game
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

        # if source == "home":
        #     self.home_window.hide()
            
        # else:
        #     self.game_window.hide()

class CustomCheckBox(QCheckBox):
    """Custom checkbox with checkmark painted inside the indicator box"""
    def paintEvent(self, event):
        super().paintEvent(event)
        
        if self.isChecked():
            # Paint checkmark inside the box
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Draw white checkmark
            painter.setPen(QPen(QColor("white"), 2.5, Qt.PenStyle.SolidLine))
            painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            
            # Calculate checkbox indicator position (usually top-left)
            x = 4
            y = (self.height() - 20) // 2 + 2
            w = 16
            h = 16
            
            # Draw checkmark with three points (smaller check inside the box)
            points = [
                QPoint(int(x + w * 0.25), int(y + h * 0.5)),
                QPoint(int(x + w * 0.4), int(y + h * 0.65)),
                QPoint(int(x + w * 0.75), int(y + h * 0.25))
            ]
            
            if len(points) >= 2:
                painter.drawLine(points[0], points[1])
                painter.drawLine(points[1], points[2])
            
            painter.end()

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(400, 380)
        
        # Modern, clean dialog styling
        self.setStyleSheet(f"""
            QDialog{{
                background: {BG_PANEL};
                border: 1px solid rgba(155, 106, 36, 0.3);
                border-radius: 20px;
                padding: 24px;
            }}

            QLabel{{
                color: {TEXT_LIGHT};
                background: transparent;
                font-family: '{FONT_KHMER}';
            }}

            QLabel#title {{
                color: {ACCENT};
                font-size: 20px;
                font-weight: 700;
                padding: 8px 0px;
                letter-spacing: 0.5px;
            }}

            QLabel#section {{
                color: {ACCENT};
                font-size: 13px;
                font-weight: 600;
                padding: 12px 0px 6px 0px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}

            QCheckBox{{
                color: {TEXT_LIGHT};
                font-family: '{FONT_KHMER}';
                font-size: 14px;
                background: transparent;
                padding: 6px 0px;
                margin: 0px;
                spacing: 8px;
            }}

            QCheckBox:hover{{
                color: {ACCENT};
            }}

            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border: 2px solid {ACCENT};
                border-radius: 5px;
                background: transparent;
                margin-right: 8px;
            }}

            QCheckBox::indicator:hover {{
                border: 2px solid {TEXT_LIGHT};
                background: rgba(255, 255, 255, 0.05);
            }}

            QCheckBox::indicator:checked {{
                background: {ACCENT};
                border: 2px solid {ACCENT};
            }}

            QPushButton{{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {ACCENT}, stop:1 {BUTTON_BG});
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 600;
                padding: 12px 24px;
                font-family: '{FONT_KHMER}';
                letter-spacing: 0.5px;
            }}

            QPushButton:hover{{
                background: {BUTTON_BG_HOVER};
                padding: 12px 26px;
            }}

            QPushButton:pressed{{
                padding: 12px 22px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        lbl = QLabel("Preferences")
        lbl.setObjectName("title")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)

        layout.addSpacing(8)

        # Audio & Animation Settings
        lbl_effects = QLabel("Audio & Effects")
        lbl_effects.setObjectName("section")
        layout.addWidget(lbl_effects)

        self.chk_sound = CustomCheckBox("Enable win sound")
        self.chk_sound.setChecked(ENABLE_WIN_SOUND)
        layout.addWidget(self.chk_sound)

        self.chk_anim = CustomCheckBox("Enable win animations")
        self.chk_anim.setChecked(ENABLE_WIN_ANIM)
        layout.addWidget(self.chk_anim)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.setContentsMargins(0, 12, 0, 0)
        btn_row.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_ok = QPushButton("OK")
        btn_cancel.setFixedHeight(44)
        btn_ok.setFixedHeight(44)
        btn_cancel.setMinimumWidth(100)
        btn_ok.setMinimumWidth(100)
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self._save)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def _save(self):
        global ENABLE_WIN_ANIM, ENABLE_WIN_SOUND
        ENABLE_WIN_ANIM = bool(self.chk_anim.isChecked())
        ENABLE_WIN_SOUND = bool(self.chk_sound.isChecked())
        self.accept()

class WinnerDialog(QDialog):
    def __init__(self, winner, parent=None):
        super().__init__(parent)

        # keep window title empty (no 'Game Over' title shown)
        self.setWindowTitle("winner")
        self.setFixedSize(500, 420)
        
        # Determine if this is a win or loss based on winner text
        self.is_player_win = "អ្នក" in winner if winner else False
        # Modern, clean dialog styling
        self.setStyleSheet(f"""
            QDialog{{
                background: {BG_PANEL};
                border: none;
                border-radius: 20px;
                padding: 0px;
            }}

            QLabel{{
                color: {TEXT_LIGHT};
                background: transparent;
                font-family: '{FONT_KHMER}';
            }}

            QLabel#trophy {{
                font-size: 72px;
                margin-bottom: 12px;
            }}

            QLabel#title {{
                color: {ACCENT};
                font-size: 24px;
                font-weight: 700;
            }}

            QLabel#subtitle {{
                color: {TEXT_LIGHT};
                font-size: 16px;
                line-height: 1.5;
            }}

            QPushButton{{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {ACCENT}, stop:1 {BUTTON_BG});
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 600;
                padding: 12px 24px;
                font-family: 'Khmer OS SiemReap';
            }}

            QPushButton:hover{{
                background: {BUTTON_BG_HOVER};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)
        self._overlay = None
        # create dim overlay on parent for focus (if parent provided)
        if parent is not None:
            try:
                self._overlay = QWidget(parent)
                self._overlay.setStyleSheet("background-color: rgba(0,0,0,0.45);")
                self._overlay.setGeometry(parent.rect())
                self._overlay.show()
            except Exception:
                self._overlay = None

        text = QLabel("ហ្គេមត្រូវបានបញ្ចប់!")
        text.setObjectName("title")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text.setStyleSheet("font-size: 24px; font-weight: bold; font-family: 'Khmer OS Muol Light'; color: #FFD700;")
        # Trophy emoji with animation
        self.trophy = QLabel()
        self.trophy.setObjectName("trophy")
        self.trophy.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.trophy.setText("🏆")
        self.trophy.setStyleSheet("font-size:60px;")

        # winner text
        self.winner_text = QLabel(winner)
        self.winner_text.setObjectName("subtitle")
        self.winner_text.setWordWrap(True)
        self.winner_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.winner_text.setMinimumWidth(380)
        self.winner_text.setMaximumWidth(420)

        # action buttons
        btn_ok = QPushButton("OK")
        btn_ok.setFixedHeight(44)
        btn_ok.setFixedWidth(120)
        btn_ok.clicked.connect(self._on_ok)

        btn_play = QPushButton("Play Again")
        btn_play.setFixedHeight(44)
        btn_play.setFixedWidth(140)
        btn_play.clicked.connect(self._on_play_again)

        # layout composition: center content with subtle spacing
        layout.addStretch(1)
        layout.addWidget(text, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.trophy, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(12)
        layout.addWidget(self.winner_text, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)
        btn_row.addStretch()
        btn_row.addWidget(btn_play)
        btn_row.addWidget(btn_ok)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # confetti containers
        self._confetti_labels = []

        # Load appropriate sound effect based on win/loss
        try:
            if ENABLE_WIN_SOUND:
                self._game_sound = QSoundEffect(self)
                # Choose sound file based on win/loss
                sound_filename = 'win.wav' if self.is_player_win else 'lose.wav'
                sound_path = QUrl.fromLocalFile(os.path.join(os.path.dirname(__file__), 'images', sound_filename))
                self._game_sound.setSource(sound_path)
                self._game_sound.setVolume(0.6)
                print(f"[DEBUG] Sound loaded: {sound_path.toLocalFile()}")
            else:
                self._game_sound = None
        except Exception as e:
            print(f"[ERROR] Failed to load sound: {e}")
            self._game_sound = None

    def _on_ok(self):
        self.choice = 'ok'
        self._close_with_cleanup()

    def _play_sound(self):
        """Play the sound effect after it's loaded"""
        try:
            if getattr(self, '_game_sound', None):
                self._game_sound.play()
                print("[DEBUG] Sound playing")
        except Exception as e:
            print(f"[ERROR] Failed to play sound: {e}")

    def _on_play_again(self):
        self.choice = 'play_again'
        self._close_with_cleanup()

    def _close_with_cleanup(self):
        # hide overlay then accept
        if self._overlay:
            try:
                self._overlay.hide()
                self._overlay.deleteLater()
            except Exception:
                pass
        self.accept()

    def showEvent(self, ev):
        super().showEvent(ev)
        
        # Play sound after a short delay to ensure it's fully loaded
        try:
            if ENABLE_WIN_SOUND and getattr(self, '_game_sound', None):
                # Use a timer to delay sound playing to ensure it's fully loaded
                QTimer.singleShot(100, self._play_sound)
        except Exception as e:
            print(f"[ERROR] Failed to schedule sound: {e}")
        
        # fade-in animation
        try:
            self.setWindowOpacity(0.0)
            fade = QPropertyAnimation(self, b"windowOpacity", self)
            fade.setDuration(400)
            fade.setStartValue(0.0)
            fade.setEndValue(1.0)
            fade.start()
        except Exception:
            pass

        # Trophy pop animation with bounce effect (increase size) - only on win
        try:
            if self.is_player_win and hasattr(self, 'trophy') and isinstance(self.trophy, QLabel):
                start, end = 40, 96
                anim = QVariantAnimation(self)
                anim.setStartValue(start)
                anim.setEndValue(end)
                anim.setDuration(600)
                
                # Add easing for bounce effect
                anim.setEasingCurve(self._create_bounce_curve())
                
                def _on_val(v):
                    val = int(v)
                    self.trophy.setStyleSheet(f"font-size:{val}px;")
                
                anim.valueChanged.connect(_on_val)
                anim.start()
                self._trophy_anim = anim
        except Exception:
            pass
        
        # Text fade-in and slide-up animation
        try:
            if hasattr(self, 'winner_text'):
                self.winner_text.setStyleSheet(self.winner_text.styleSheet() + "; opacity: 0;")
                text_anim = QPropertyAnimation(self, b"windowOpacity", self)
                text_anim.setDuration(500)
                text_anim.setStartValue(0.0)
                text_anim.setEndValue(1.0)
                text_anim.setDelay(200)
                # Note: This won't work as intended, using a timer instead
        except Exception:
            pass

        # Start confetti animation (only on win)
        try:
            if ENABLE_WIN_ANIM and self.is_player_win:
                self._start_confetti()
        except Exception:
            pass
    
    def _create_bounce_curve(self):
        """Create a custom easing curve for bounce effect"""
        from PyQt6.QtCore import QEasingCurve
        # Use OutBounce easing for a nice bounce effect
        return QEasingCurve(QEasingCurve.Type.OutBounce)

    def _start_confetti(self):
        import random
        parent_rect = self.geometry()
        confetti_emojis = ['🎉', '⭐', '✨', '🎊', '🌟', '💫']
        
        # Create more confetti for more impressive effect
        for i in range(30):
            lbl = QLabel(self)
            emoji = random.choice(confetti_emojis)
            lbl.setText(emoji)
            size = random.randint(14, 28)
            lbl.setStyleSheet(f"font-size: {size}px; color: {ACCENT};")
            lbl.adjustSize()
            
            start_x = random.randint(20, parent_rect.width() - 20)
            start_y = -30
            lbl.move(start_x, start_y)
            lbl.show()
            self._confetti_labels.append(lbl)

            # Falling animation with longer duration for better effect
            anim = QPropertyAnimation(lbl, b"pos", self)
            duration = 1500 + random.randint(0, 600)
            anim.setDuration(duration)
            
            end_x = start_x + random.randint(-80, 80)
            end_y = parent_rect.height() + 30
            
            anim.setStartValue(QPoint(start_x, start_y))
            anim.setEndValue(QPoint(end_x, end_y))
            
            # Add easing for more natural falling
            from PyQt6.QtCore import QEasingCurve
            anim.setEasingCurve(QEasingCurve(QEasingCurve.Type.InQuad))
            
            anim.start()
            self._confetti_anims = getattr(self, '_confetti_anims', [])
            self._confetti_anims.append(anim)
##UI for Continue
class SaveSuccessDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("រក្សាទុក")
        self.setFixedSize(450, 260)

        self.setStyleSheet(f"""
            QDialog{{
                background-color:{BG_PANEL};
                border:2px solid {SEPARATOR};
                border-radius:20px;
            }}

            QLabel{{
                color:{TEXT_LIGHT};
                background:transparent;
            }}

            QPushButton{{
                background-color:{ACCENT};
                color:white;
                border:none;
                border-radius:10px;
                font-size:14px;
                font-weight:bold;
                padding:10px;
            }}

            QPushButton:hover{{
                background-color:{BUTTON_BG_HOVER};
            }}
        """)

        layout = QVBoxLayout(self)

        icon = QLabel("💾")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size:60px;")

        title = QLabel("រក្សាទុកបានជោគជ័យ")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"""
            color: {ACCENT};
            font-size:24px;
            font-family:'Khmer OS SiemReap';
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

        self.setStyleSheet(f"""
            QDialog{{
                background-color:{BG_PANEL};
                border:2px solid {SEPARATOR};
                border-radius:20px;
            }}

            QLabel{{
                color:{TEXT_LIGHT};
                background:transparent;
            }}

            QPushButton{{
                border-radius:12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25,25,25,25)
        layout.setSpacing(15)

        title = QLabel("ល្បែងរែក")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"""
            color: {ACCENT};
            font-size:28px;
            font-family:'Khmer OS Muol Light';
        """)

        subtitle = QLabel("ជ្រើសរើសរបៀបលេង")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"""
            font-size:15px;
            color: {TEXT_LIGHT};
        """)

        btn_new = QPushButton(
            "🎮 ហ្គេមថ្មី"
        )
        btn_new.setFixedHeight(75)
        btn_new.setStyleSheet(f"""
            QPushButton{{
                background: green;
                color: white;
                font-size:14px;
                font-family:'Khmer OS Muol Light';
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 14px;
            }}
            QPushButton:hover{{
                background: {BUTTON_BG_HOVER};
                
            }}
        """)

        btn_continue = QPushButton(
            "💾  បន្តហ្គេម"
        )
        btn_continue.setFixedHeight(75)
        btn_continue.setStyleSheet(f"""
            QPushButton{{
                background: blue;
                color: white;
                font-size:14px;
                font-family:'Khmer OS Muol Light';
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 14px;
            }}
            QPushButton:hover{{
                background: {BUTTON_BG_HOVER};
            }}
        """)

        btn_cancel = QPushButton("បោះបង់")
        btn_cancel.setFixedHeight(45)
        btn_cancel.setStyleSheet(f"""
            QPushButton{{
                background: red;
                color: {TEXT_LIGHT};
                border:1px solid rgba(255,255,255,0.08);
                font-family:'Khmer OS Muol Light';
                border-radius: 12px;
            }}

            QPushButton:hover{{
                background: {BUTTON_BG_HOVER};
            }}
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
##History Dailog
class HistoryDialog(QDialog):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("ប្រវត្តិការលេង")
        self.resize(900, 520)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {BG_DARK};
                border: 1px solid {SEPARATOR};
                border-radius: 22px;
            }}
            QLabel {{
                color: {TEXT_LIGHT};
            }}
            QTableWidget {{
                background-color: {BG_PANEL};
                color: {TEXT_LIGHT};
                border: 1px solid {SEPARATOR};
                gridline-color: {SEPARATOR};
            }}
            QTableWidget::item {{
                padding: 10px;
            }}
            QHeaderView::section {{
                background-color: {BOARD_LIGHT};
                color: {TEXT_LIGHT};
                padding: 10px;
                border: 1px solid {SEPARATOR};
                border-radius: 10px;
            }}
            QPushButton {{
                background-color: {ACCENT};
                color: white;
                border: none;
                border-radius: 12px;
                padding: 10px 14px;
            }}
            QPushButton:hover {{
                background-color: {BUTTON_BG_HOVER};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("ប្រវត្តិការប្រកួត")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-family: 'Khmer OS Muol Light';")

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Player", "Mode", "Result", "Date"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        history = load_history()
        self.table.setRowCount(len(history))

        for row_idx, row in enumerate(history):
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(row[0] or "")))
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(row[1] or "")))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(row[2] or "")))
            self.table.setItem(row_idx, 3, QTableWidgetItem(str(row[3] or "")))

        btn = QPushButton("បិទ")
        btn.setFixedWidth(100)
        btn.clicked.connect(self.accept)

        layout.addWidget(title)
        layout.addWidget(self.table)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignRight)
if __name__ == "__main__":
    create_tables()
    app = QApplication(sys.argv)
    app.setFont(QFont(FONT_KHMER, 10))
    # Global lightweight stylesheet to ensure consistent, clean typography
    app.setStyleSheet(f"""
        QWidget {{
            font-family: '{FONT_KHMER}';
            color: {TEXT_LIGHT};
        }}
        QPushButton {{
            font-family: '{FONT_KHMER}';
            padding: 8px 12px;
        }}
        QLabel[heading="true"] {{
            color: {ACCENT};
        }}
    """)
    controller = GameController()
    controller.start()
    sys.exit(app.exec())