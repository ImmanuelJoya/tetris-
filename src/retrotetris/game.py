#!/usr/bin/env python3
"""
RETRO TETRIS - Dark Terminal Edition
A multi-panel Tetris TUI inspired by classic terminal Tetris clients,
forced to a dark color scheme regardless of your terminal's theme.
Pure Python standard library - no dependencies.

Controls:
  h / Left / a     - move left
  l / Right / d    - move right
  j / Down / s     - soft drop
  k / Up / w / x   - rotate clockwise
  z                - rotate counter-clockwise
  space            - hard drop
  p                - pause / resume
  q                - quit
"""

import curses
import locale
import os
import random
import time

try:
    locale.setlocale(locale.LC_ALL, "")
except locale.Error:
    pass

HIGHSCORE_PATH = os.path.expanduser("~/.retrotetris_highscore")

BOARD_COLS = 10
BOARD_ROWS = 20
CELL_W = 2

# --- Color pair numbers ----------------------------------------------------
PAIR_TEXT = 1
PAIR_BORDER = 2
PAIR_TITLE = 3
PAIR_VALUE = 4
PAIR_GAMEOVER = 5
PAIR_HIGHLIGHT = 6

FILL_PAIR = {}
GHOST_PAIR = {}

PIECE_COLOR_BASE = {}  # populated after curses starts (needs curses module constants)

PIECES = {
    "I": {"shape": ["....", "####", "....", "...."]},
    "O": {"shape": ["##", "##"]},
    "T": {"shape": [".#.", "###", "..."]},
    "S": {"shape": [".##", "##.", "..."]},
    "Z": {"shape": ["##.", ".##", "..."]},
    "J": {"shape": ["#..", "###", "..."]},
    "L": {"shape": ["..#", "###", "..."]},
}

LINE_SCORES = {1: 100, 2: 300, 3: 500, 4: 800}

FONT = {
    "T": ["#####", "  #  ", "  #  ", "  #  ", "  #  "],
    "E": ["#####", "#    ", "#### ", "#    ", "#####"],
    "R": ["#### ", "#   #", "#### ", "#  # ", "#   #"],
    "I": ["  #  ", "  #  ", "  #  ", "  #  ", "  #  "],
    "S": [" ####", "#    ", " ### ", "    #", "#### "],
    " ": ["   ", "   ", "   ", "   ", "   "],
}


# --- Small drawing helpers --------------------------------------------------

def safe_addstr(win, y, x, s, color_pair=0, attr=0):
    try:
        win.addstr(y, x, s, curses.color_pair(color_pair) | attr)
    except curses.error:
        pass


def center_x(width, text):
    return max(0, (width - len(text)) // 2)


def text_big_width(text):
    width = 0
    for ch in text.upper():
        pattern = FONT.get(ch, FONT[" "])
        width += len(pattern[0]) + 1
    return max(width - 1, 0)


def draw_text_big(win, text, top_y, left_x, color_pair, attr=0):
    col = left_x
    for ch in text.upper():
        pattern = FONT.get(ch, FONT[" "])
        for row_idx, row in enumerate(pattern):
            for col_idx, px in enumerate(row):
                if px == "#":
                    safe_addstr(win, top_y + row_idx, col + col_idx, "#", color_pair, attr)
        col += len(pattern[0]) + 1


def load_highscore():
    try:
        with open(HIGHSCORE_PATH) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return 0


def save_highscore(score):
    try:
        with open(HIGHSCORE_PATH, "w") as f:
            f.write(str(score))
    except OSError:
        pass


def init_colors(stdscr):
    curses.start_color()
    bg = curses.COLOR_BLACK
    curses.init_pair(PAIR_TEXT, curses.COLOR_WHITE, bg)
    curses.init_pair(PAIR_BORDER, curses.COLOR_CYAN, bg)
    curses.init_pair(PAIR_TITLE, curses.COLOR_WHITE, bg)
    curses.init_pair(PAIR_VALUE, curses.COLOR_YELLOW, bg)
    curses.init_pair(PAIR_GAMEOVER, curses.COLOR_RED, bg)
    curses.init_pair(PAIR_HIGHLIGHT, curses.COLOR_GREEN, bg)

    PIECE_COLOR_BASE.update({
        "I": curses.COLOR_CYAN,
        "O": curses.COLOR_YELLOW,
        "T": curses.COLOR_MAGENTA,
        "S": curses.COLOR_GREEN,
        "Z": curses.COLOR_RED,
        "J": curses.COLOR_BLUE,
        "L": curses.COLOR_WHITE,
    })

    pair_num = 10
    for ptype, color in PIECE_COLOR_BASE.items():
        FILL_PAIR[ptype] = pair_num
        curses.init_pair(pair_num, curses.COLOR_BLACK, color)
        pair_num += 1
        GHOST_PAIR[ptype] = pair_num
        curses.init_pair(pair_num, color, bg)
        pair_num += 1

    # Force a dark background across the whole screen, regardless of the
    # user's terminal theme.
    stdscr.bkgd(" ", curses.color_pair(PAIR_TEXT))


# --- Piece helpers -----------------------------------------------------

def shape_to_grid(shape):
    return [[c == "#" for c in row] for row in shape]


def rotate_cw(grid):
    n = len(grid)
    return [[grid[n - 1 - c][r] for c in range(n)] for r in range(n)]


def rotate_ccw(grid):
    n = len(grid)
    return [[grid[c][n - 1 - r] for c in range(n)] for r in range(n)]


def new_piece(piece_type):
    grid = shape_to_grid(PIECES[piece_type]["shape"])
    n = len(grid)
    return {
        "type": piece_type,
        "grid": grid,
        "row": 0,
        "col": (BOARD_COLS - n) // 2,
    }


def draw_bag():
    bag = list(PIECES.keys())
    random.shuffle(bag)
    return bag


def valid_position(board, grid, row, col):
    n = len(grid)
    for r in range(n):
        for c in range(n):
            if grid[r][c]:
                br, bc = row + r, col + c
                if bc < 0 or bc >= BOARD_COLS or br >= BOARD_ROWS:
                    return False
                if br >= 0 and board[br][bc] is not None:
                    return False
    return True


def ghost_drop_row(board, piece):
    row = piece["row"]
    while valid_position(board, piece["grid"], row + 1, piece["col"]):
        row += 1
    return row


def lock_piece(board, piece):
    n = len(piece["grid"])
    for r in range(n):
        for c in range(n):
            if piece["grid"][r][c]:
                br, bc = piece["row"] + r, piece["col"] + c
                if 0 <= br < BOARD_ROWS:
                    board[br][bc] = piece["type"]


def clear_lines(board):
    kept = [row for row in board if any(cell is None for cell in row)]
    cleared = BOARD_ROWS - len(kept)
    for _ in range(cleared):
        kept.insert(0, [None] * BOARD_COLS)
    return kept, cleared


def gravity_delay_ms(level):
    return max(100, 800 - level * 70)


# --- Layout ------------------------------------------------------------

def compute_layout():
    margin = 2

    stats_w, stats_h = 20, 6
    stats_top, stats_left = 1, 1
    stats_bottom = stats_top + stats_h - 1
    stats_right = stats_left + stats_w - 1

    board_w = BOARD_COLS * CELL_W
    board_h = BOARD_ROWS
    tetris_top = 1
    tetris_left = stats_right + 1 + margin
    pf_top = tetris_top + 1
    pf_left = tetris_left + 1
    tetris_bottom = pf_top + board_h
    tetris_right = pf_left + board_w

    next_w, next_h = 16, 7
    next_top = 1
    next_left = tetris_right + 1 + margin
    next_bottom = next_top + next_h - 1
    next_right = next_left + next_w - 1

    help_w, help_h = 24, 9
    help_left = next_left
    help_top = next_bottom + 1 + margin
    help_bottom = help_top + help_h - 1
    help_right = help_left + help_w - 1

    min_w = max(tetris_right, help_right, next_right) + 2
    min_h = max(tetris_bottom, help_bottom) + 2

    return {
        "stats": (stats_top, stats_left, stats_bottom, stats_right),
        "tetris": (tetris_top, tetris_left, tetris_bottom, tetris_right),
        "pf_top": pf_top,
        "pf_left": pf_left,
        "next": (next_top, next_left, next_bottom, next_right),
        "help": (help_top, help_left, help_bottom, help_right),
        "min_w": min_w,
        "min_h": min_h,
    }


# --- Panel drawing -------------------------------------------------------

def draw_panel(stdscr, top, left, bottom, right, title=None):
    safe_addstr(stdscr, top, left, "┌", PAIR_BORDER)
    safe_addstr(stdscr, top, right, "┐", PAIR_BORDER)
    safe_addstr(stdscr, bottom, left, "└", PAIR_BORDER)
    safe_addstr(stdscr, bottom, right, "┘", PAIR_BORDER)
    for x in range(left + 1, right):
        safe_addstr(stdscr, top, x, "─", PAIR_BORDER)
        safe_addstr(stdscr, bottom, x, "─", PAIR_BORDER)
    for y in range(top + 1, bottom):
        safe_addstr(stdscr, y, left, "│", PAIR_BORDER)
        safe_addstr(stdscr, y, right, "│", PAIR_BORDER)
    if title:
        label = f" {title} "
        tx = left + max(1, (right - left - len(label)) // 2)
        safe_addstr(stdscr, top, tx, label, PAIR_TITLE, curses.A_BOLD)


def draw_stats_panel(stdscr, layout, score, level, lines, high_score):
    top, left, bottom, right = layout["stats"]
    draw_panel(stdscr, top, left, bottom, right, "Stats")
    rows = [
        ("SCORE", score),
        ("LEVEL", level),
        ("LINES", lines),
        ("HIGH", high_score),
    ]
    for i, (label, value) in enumerate(rows):
        line = f"{label:<8}{value:>10}"
        safe_addstr(stdscr, top + 1 + i, left + 1, line, PAIR_TEXT, curses.A_BOLD)
        safe_addstr(stdscr, top + 1 + i, left + 9, f"{value:>10}", PAIR_VALUE, curses.A_BOLD)


def draw_next_panel(stdscr, layout, next_type):
    top, left, bottom, right = layout["next"]
    draw_panel(stdscr, top, left, bottom, right, "Next")
    grid = shape_to_grid(PIECES[next_type]["shape"])
    n = len(grid)
    interior_h = (bottom - top - 1)
    interior_cells_w = (right - left - 1) // CELL_W
    off_r = max(0, (interior_h - n) // 2)
    off_c = max(0, (interior_cells_w - n) // 2)
    fill = FILL_PAIR[next_type]
    for r in range(n):
        for c in range(n):
            if grid[r][c]:
                y = top + 1 + off_r + r
                x = left + 1 + (off_c + c) * CELL_W
                safe_addstr(stdscr, y, x, "  ", fill)


def draw_help_panel(stdscr, layout):
    top, left, bottom, right = layout["help"]
    draw_panel(stdscr, top, left, bottom, right, "Help")
    lines = [
        "MOVE       H L  / <-  ->",
        "SOFT DROP  J    / DOWN",
        "ROTATE CW  K    / UP",
        "ROTATE CCW Z",
        "HARD DROP  SPACE",
        "PAUSE      P",
        "QUIT       Q",
    ]
    for i, line in enumerate(lines):
        safe_addstr(stdscr, top + 1 + i, left + 1, line, PAIR_TEXT)


def draw_board_panel(stdscr, layout, board, piece):
    top, left, bottom, right = layout["tetris"]
    pf_top, pf_left = layout["pf_top"], layout["pf_left"]
    draw_panel(stdscr, top, left, bottom, right, "Tetris")

    for r in range(BOARD_ROWS):
        for c in range(BOARD_COLS):
            cell = board[r][c]
            y, x = pf_top + r, pf_left + c * CELL_W
            if cell is None:
                safe_addstr(stdscr, y, x, " \u00b7", PAIR_TEXT, curses.A_DIM)
            else:
                safe_addstr(stdscr, y, x, "  ", FILL_PAIR[cell])

    if piece is not None:
        ghost_row = ghost_drop_row(board, piece)
        n = len(piece["grid"])
        ghost_pair = GHOST_PAIR[piece["type"]]
        for r in range(n):
            for c in range(n):
                if piece["grid"][r][c]:
                    gr, gc = ghost_row + r, piece["col"] + c
                    if 0 <= gr < BOARD_ROWS and ghost_row != piece["row"]:
                        safe_addstr(stdscr, pf_top + gr, pf_left + gc * CELL_W, "::", ghost_pair, curses.A_DIM)

        fill = FILL_PAIR[piece["type"]]
        for r in range(n):
            for c in range(n):
                if piece["grid"][r][c]:
                    pr, pc = piece["row"] + r, piece["col"] + c
                    if 0 <= pr < BOARD_ROWS:
                        safe_addstr(stdscr, pf_top + pr, pf_left + pc * CELL_W, "  ", fill)


def draw_pause_overlay(stdscr, layout):
    top, left, bottom, right = layout["tetris"]
    msg = " PAUSED "
    cy = (top + bottom) // 2
    cx = left + (right - left - len(msg)) // 2
    safe_addstr(stdscr, cy, cx, msg, PAIR_HIGHLIGHT, curses.A_BOLD | curses.A_REVERSE | curses.A_BLINK)


def draw_game_over_overlay(stdscr, layout, score, high_score, new_record):
    top, left, bottom, right = layout["tetris"]
    box_w, box_h = 26, 7
    box_top = (top + bottom) // 2 - box_h // 2
    box_left = left + ((right - left) - box_w) // 2
    box_bottom = box_top + box_h - 1
    box_right = box_left + box_w - 1

    for y in range(box_top, box_bottom + 1):
        safe_addstr(stdscr, y, box_left, " " * (box_w + 1), PAIR_TEXT)
    draw_panel(stdscr, box_top, box_left, box_bottom, box_right, "Game Over")

    lines = [
        f"SCORE: {score}",
        ("NEW HIGH SCORE!" if new_record else f"HIGH SCORE: {high_score}"),
        "",
        "PRESS ANY KEY",
    ]
    for i, line in enumerate(lines):
        color = PAIR_HIGHLIGHT if (i == 1 and new_record) else PAIR_TEXT
        attr = curses.A_BOLD | (curses.A_BLINK if (i == 1 and new_record) else 0)
        safe_addstr(stdscr, box_top + 2 + i, box_left + center_x(box_w - 1, line) + 1, line, color, attr)


# --- Screens -------------------------------------------------------------

def title_and_level_select(stdscr, high_score, layout):
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    level = 0

    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()

        title_w = text_big_width("TETRIS")
        draw_text_big(stdscr, "TETRIS", 2, max(0, (w - title_w) // 2), PAIR_BORDER, curses.A_BOLD)

        sub = "DARK TERMINAL EDITION"
        safe_addstr(stdscr, 9, center_x(w, sub), sub, PAIR_TEXT, curses.A_BOLD)

        hs = f"HIGH SCORE: {high_score}"
        safe_addstr(stdscr, 11, center_x(w, hs), hs, PAIR_VALUE, curses.A_BOLD)

        lvl_line = f"STARTING LEVEL:   <  {level}  >"
        safe_addstr(stdscr, 14, center_x(w, lvl_line), lvl_line, PAIR_HIGHLIGHT, curses.A_BOLD)

        hint = "LEFT/RIGHT TO CHANGE LEVEL   ENTER OR SPACE TO START"
        safe_addstr(stdscr, 16, center_x(w, hint), hint, PAIR_TEXT, 0)

        controls = "H J K L / ARROWS / WASD   SPACE DROP   P PAUSE   Q QUIT"
        safe_addstr(stdscr, 18, center_x(w, controls), controls, PAIR_TEXT, curses.A_DIM)

        stdscr.refresh()
        key = stdscr.getch()

        if key in (curses.KEY_LEFT, ord("h"), ord("H"), ord("a"), ord("A")):
            level = max(0, level - 1)
        elif key in (curses.KEY_RIGHT, ord("l"), ord("L"), ord("d"), ord("D")):
            level = min(9, level + 1)
        elif key in (10, 13, ord(" ")):
            return level
        elif key in (ord("q"), ord("Q")):
            return None


def play_round(stdscr, high_score, start_level, layout):
    board = [[None] * BOARD_COLS for _ in range(BOARD_ROWS)]

    queue = draw_bag() + draw_bag()
    piece = new_piece(queue.pop(0))
    next_type = queue[0]

    score = 0
    lines_cleared_total = 0
    paused = False
    natural_game_over = False

    last_drop = time.monotonic()
    stdscr.nodelay(True)

    def current_level():
        return start_level + lines_cleared_total // 10

    def refill_queue():
        if len(queue) < 7:
            queue.extend(draw_bag())

    def spawn_next():
        nonlocal piece, next_type
        refill_queue()
        piece = new_piece(queue.pop(0))
        next_type = queue[0]
        refill_queue()
        return valid_position(board, piece["grid"], piece["row"], piece["col"])

    def lock_and_clear():
        nonlocal board, score, lines_cleared_total
        lock_piece(board, piece)
        board, cleared = clear_lines(board)
        if cleared:
            score += LINE_SCORES.get(cleared, cleared * 200) * (current_level() + 1)
            lines_cleared_total += cleared

    while True:
        level = current_level()
        stdscr.erase()
        draw_stats_panel(stdscr, layout, score, level, lines_cleared_total, high_score)
        draw_board_panel(stdscr, layout, board, piece)
        draw_next_panel(stdscr, layout, next_type)
        draw_help_panel(stdscr, layout)
        if paused:
            draw_pause_overlay(stdscr, layout)
        stdscr.refresh()

        stdscr.timeout(30)
        key = stdscr.getch()

        if key in (ord("p"), ord("P")):
            paused = not paused
            last_drop = time.monotonic()
            continue
        if key in (ord("q"), ord("Q")):
            return score
        if paused:
            continue

        moved_this_frame = False

        if key in (curses.KEY_LEFT, ord("h"), ord("H"), ord("a"), ord("A")):
            if valid_position(board, piece["grid"], piece["row"], piece["col"] - 1):
                piece["col"] -= 1
        elif key in (curses.KEY_RIGHT, ord("l"), ord("L"), ord("d"), ord("D")):
            if valid_position(board, piece["grid"], piece["row"], piece["col"] + 1):
                piece["col"] += 1
        elif key in (curses.KEY_UP, ord("k"), ord("K"), ord("w"), ord("W"), ord("x"), ord("X")):
            new_grid = rotate_cw(piece["grid"])
            for kick in (0, -1, 1, -2, 2):
                if valid_position(board, new_grid, piece["row"], piece["col"] + kick):
                    piece["grid"] = new_grid
                    piece["col"] += kick
                    break
        elif key in (ord("z"), ord("Z")):
            new_grid = rotate_ccw(piece["grid"])
            for kick in (0, -1, 1, -2, 2):
                if valid_position(board, new_grid, piece["row"], piece["col"] + kick):
                    piece["grid"] = new_grid
                    piece["col"] += kick
                    break
        elif key in (curses.KEY_DOWN, ord("j"), ord("J"), ord("s"), ord("S")):
            if valid_position(board, piece["grid"], piece["row"] + 1, piece["col"]):
                piece["row"] += 1
                score += 1
                moved_this_frame = True
            else:
                lock_and_clear()
                if not spawn_next():
                    natural_game_over = True
        elif key == ord(" "):
            drop_to = ghost_drop_row(board, piece)
            score += (drop_to - piece["row"]) * 2
            piece["row"] = drop_to
            lock_and_clear()
            if not spawn_next():
                natural_game_over = True
            moved_this_frame = True

        if natural_game_over:
            break

        now = time.monotonic()
        if not moved_this_frame and (now - last_drop) * 1000 >= gravity_delay_ms(level):
            last_drop = now
            if valid_position(board, piece["grid"], piece["row"] + 1, piece["col"]):
                piece["row"] += 1
            else:
                lock_and_clear()
                if not spawn_next():
                    natural_game_over = True
                    break
        elif moved_this_frame:
            last_drop = now

    # Natural game over: freeze the board, show overlay, wait for a key.
    new_record = score > high_score
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    stdscr.erase()
    draw_stats_panel(stdscr, layout, score, current_level(), lines_cleared_total, high_score)
    draw_board_panel(stdscr, layout, board, None)
    draw_next_panel(stdscr, layout, next_type)
    draw_help_panel(stdscr, layout)
    draw_game_over_overlay(stdscr, layout, score, high_score, new_record)
    stdscr.refresh()
    stdscr.getch()
    return score


def run(stdscr):
    curses.curs_set(0)
    init_colors(stdscr)
    stdscr.keypad(True)

    layout = compute_layout()
    high_score = load_highscore()

    while True:
        start_level = title_and_level_select(stdscr, high_score, layout)
        if start_level is None:
            return

        score = play_round(stdscr, high_score, start_level, layout)
        if score > high_score:
            high_score = score
            save_highscore(high_score)


def main():
    layout = compute_layout()
    rows_ok = cols_ok = True
    try:
        import shutil
        cols, rows = shutil.get_terminal_size()
        rows_ok = rows >= layout["min_h"]
        cols_ok = cols >= layout["min_w"]
    except Exception:
        pass

    if not (rows_ok and cols_ok):
        print("Your terminal is a little small for RETRO TETRIS.")
        print(f"Please resize it to at least {layout['min_w']}x{layout['min_h']} and try again.")
        return

    try:
        curses.wrapper(run)
    except KeyboardInterrupt:
        pass
    print("Thanks for playing RETRO TETRIS!")
 

if __name__ == "__main__":
    main()
