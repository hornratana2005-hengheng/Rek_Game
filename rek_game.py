import sys
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
                             QTableWidgetItem, QHeaderView, QLineEdit)
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
        deadline = time.perf_counter() + 1.85

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
        self.ai_thinking = False
        
        self.seconds_elapsed = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_time)

        self.setWindowTitle("ល្បែងរែក - Rek Strategic Game")
        self.resize(1350, 820)
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
        header_title.setStyleSheet(
            "color: #ca8b47; font-size: 24px; "
            "font-family: 'Khmer OS Muol Light'; "
            "line-height: 40px; border-bottom: 2px solid #6a4b18; "
            "padding-bottom: 15px;"
        )
        left_layout.addWidget(header_title)

        # ===== Player Name =====
        player_name = load_player_name() or "Player"

        self.lbl_player = QLabel(f"👤 {player_name}")
        self.lbl_player.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_player.setStyleSheet("""
            color: #ecc06a;
            font-size: 14px;
            font-weight: bold;
            padding: 8px;
        """)
        left_layout.addWidget(self.lbl_player)

        # ===== Menu Buttons =====
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
        self.lbl_ai_status = self._create_info_label("🤖 AI : Your turn")
        
        right_layout.addWidget(self.lbl_time)
        right_layout.addWidget(self.lbl_moves)
        right_layout.addWidget(self.lbl_mode)
        right_layout.addWidget(self.lbl_ai_status)

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
            self.lbl_turn_en.setText("TURN : LIGHT GREEN")
            self.ai_thinking = True
            self._set_ai_status("thinking...")
            if not self.game_over:
                QApplication.processEvents()
                QTimer.singleShot(2000, self._trigger_ai_move)
        else:
            self.current_player = 'L' if self.current_player == 'G' else 'G'
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

        if not g_king or g_count == 0:
            winner = "ក្រុមបៃតងខ្ចី (AI/Sok) ឈ្នះ!"
        elif not l_king or l_count == 0:
            winner = "ក្រុមបៃតង (អ្នក) ឈ្នះ!"

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

        dlg = WinnerDialog(winner)
        dlg.exec()

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
        self.resize(1000, 700)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("background-color: #1f1105;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(80, 80, 80, 80)
        layout.setSpacing(20)

        card = QFrame()
        card.setStyleSheet("background-color: #110903; border: 2px solid #6a4b18; border-radius: 20px;")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(16)

        title = QLabel("Welcome to Rek Game")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #ca8b47; font-size: 28px; font-family: 'Khmer OS Muol Light';")

        subtitle = QLabel("Enter your name to continue")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #f7e6c4; font-size: 16px;")

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Your name...")
        self.name_input.setFixedHeight(48)
        self.name_input.setStyleSheet("background-color: #1f1105; color: white; border: 1px solid #6a4b18; border-radius: 10px; padding-left: 12px; font-size: 15px;")
        self.name_input.returnPressed.connect(self.login)

        saved_name = load_player_name()
        if saved_name:
            self.name_input.setText(saved_name)

        btn_login = QPushButton("Login")
        btn_login.setFixedHeight(50)
        btn_login.setStyleSheet("QPushButton { background-color: #009a49; color: white; border-radius: 10px; font-size: 15px; font-weight: bold; } QPushButton:hover { background-color: #00b85a; }")
        btn_login.clicked.connect(self.login)

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addWidget(self.name_input)
        card_layout.addWidget(btn_login)
        layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

    def login(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Login", "Please enter your name.")
            return

        save_player_name(name)
        self.controller.show_home()


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
        wins, loses = get_stats()

        stats = QLabel(
            f"🏆 Wins : {wins}\n❌ Loses : {loses}"
        )

        stats.setAlignment(Qt.AlignmentFlag.AlignCenter)

        stats.setStyleSheet("""
            color:#ecc06a;
            font-size:16px;
            font-weight:bold;
            border:1px solid #ecc06a;
            border-radius:10px;
            padding:10px;
            background-color:#8a5720;
""")
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
        self.btn_history = self._create_menu_btn("🏆 ប្រវត្តិការលេង (History)","#9f672b")       
        self.btn_exit = self._create_menu_btn("✕   ចាកចេញ (Exit)", "#9f672b")
        self.btn_logout = self._create_menu_btn("⇥   Logout", "#8c4e2d")
        

        self.btn_ai.clicked.connect(self.show_ai_dialog)
        self.btn_player.clicked.connect(lambda: self.controller.start_game("player"))
        self.btn_rules.clicked.connect(lambda: self.controller.show_rules("home"))
        self.btn_logout.clicked.connect(self.logout)
        self.btn_history.clicked.connect(
    self.show_history
)
        self.btn_exit.clicked.connect(self.close)

        right_layout.addWidget(self.btn_ai)
        right_layout.addSpacing(30)
        right_layout.addWidget(self.btn_player)
        right_layout.addSpacing(30)
        right_layout.addWidget(self.btn_rules)
        right_layout.addSpacing(20)
        right_layout.addWidget(self.btn_history)
        right_layout.addSpacing(20)
        right_layout.addWidget(self.btn_exit)
        right_layout.addSpacing(20)
        right_layout.addWidget(self.btn_logout)
        right_layout.addStretch()
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, 1)
        
        
    def show_history(self):
        dlg = HistoryDialog()
        dlg.exec()

    def logout(self):
        clear_player_name()
        QMessageBox.information(self, "Logout", "Your saved name has been cleared. The next new game will ask for a new name.")
        self.controller.show_login()

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
# ១០. អ្នកគ្រប់គ្រងកម្មវិធី (CONTROLLER & MAIN)
# ==========================================
class GameController:
    def __init__(self):
        self.login_window = LoginUI(self)
        self.home_window = HomeUI(self)
        self.game_window = None
        self.rules_window = None
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
        self.home_window.show()
        if self.login_window:
            self.login_window.hide()
        if self.game_window:
            self.game_window.hide()
        if self.rules_window:
            self.rules_window.hide()

    def logout(self):
        clear_player_name()
        if self.game_window:
            self.game_window.close()
            self.game_window = None
        self.show_login()

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
##History Dailog
class HistoryDialog(QDialog):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("ប្រវត្តិការលេង")
        self.resize(900, 520)
        self.setStyleSheet("""
            QDialog {
                background-color: #110903;
                border: 2px solid #6a4b18;
            }
            QLabel {
                color: #f7e6c4;
            }
            QTableWidget {
                background-color: #1f1105;
                color: white;
                border: 1px solid #6a4b18;
                gridline-color: #6a4b18;
            }
            QHeaderView::section {
                background-color: #381c06;
                color: #ca8b47;
                padding: 6px;
                border: 1px solid #6a4b18;
            }
            QPushButton {
                background-color: #381c06;
                color: #ca8b47;
                border: 1px solid #6a4b18;
                border-radius: 8px;
                padding: 8px 14px;
            }
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
        btn.clicked.connect(self.accept)

        layout.addWidget(title)
        layout.addWidget(self.table)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignRight)
if __name__ == "__main__":
    create_tables()
    app = QApplication(sys.argv)
    app.setFont(QFont("Khmer OS Battambang", 10))
    controller = GameController()
    controller.show_home()
    sys.exit(app.exec())