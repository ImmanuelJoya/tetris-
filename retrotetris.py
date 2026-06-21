#!/usr/bin/env python3
"""
RETRO TETRIS - Terminal Edition
A classic falling-blocks game with retro arcade styling, playable
entirely inside your terminal. No dependencies beyond Python's
standard library.

Controls:
  Left/Right or A/D   - move
  Down or S           - soft drop
  Up/W or X           - rotate clockwise
  Z                   - rotate counter-clockwise
  Space               - hard drop
  P                   - pause / resume
  Q                   - quit
"""

import curses
import os
import random
import time

HIGHSCORE_PATH = os.path.expanduser("~/.retrotetris_highscore")

BOARD_COLS = 10
BOARD_ROWS = 20
CELL_W = 2  # terminal columns per board cell, for a square-ish look

# --- Blocky 5-row "LED sign" font, used for big titles -------------------
FONT = {
    "T": ["#####", "  #  ", "  #  ", "  #  ", "  #  "],
    "E": ["#####", "#    ", "#### ", "#    ", "#####"],
    "R": ["#### ", "#   #", "#### ", "#  # ", "#   #"],
    "I": ["  #  ", "  #  ", "  #  ", "  #  ", "  #  "],
    "S": [" ####", "#    ", " ### ", "    #", "#### "],
    "G": [" ####", "#    ", "#  ##", "#   #", " ####"],
    "A": [" ### ", "#   #", "#####", "#   #", "#   #"],
    "M": ["#   #", "## ##", "# # #", "#   #", "#   #"],
    "O": [" ### ", "#   #", "#   #", "#   #", " ### "],
    "V": ["#   #", "#   #", "#   #", " # # ", "  #  "],
    " ": ["   ", "   ", "   ", "   ", "   "],
}

# Color pair numbers
C_I, C_O, C_T, C_S, C_Z, C_J, C_L = 1, 2, 3, 4, 5, 6, 7
C_TEXT, C_BORDER, C_GHOST = 8, 9, 10

PIECES = {
    "I": {"shape": ["....", "####", "....", "...."], "color": C_I},
    "O": {"shape": ["##", "##"], "color": C_O},
    "T": {"shape": [".#.", "###", "..."], "color": C_T},
    "S": {"shape": [".##", "##.", "..."], "color": C_S},
    "Z": {"shape": ["##.", ".##", "..."], "color": C_Z},
    "J": {"shape": ["#..", "###", "..."], "color": C_J},
    "L": {"shape": ["..#", "###", "..."], "color": C_L},
}

LINE_SCORES = {1: 100, 2: 300, 3: 500, 4: 800}


# --- Small drawing helpers -------------------------------------------------

def safe_addstr(win, y, x, s, color_pair=0, attr=0):
    try:
        win.addstr(y, x, s, curses.color_pair(color_pair) | attr)
    except curses.error:
        pass


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


def init_colors():
    curses.start_color()
    try:
        curses.use_default_colors()
        bg = -1
    except curses.error:
        bg = curses.COLOR_BLACK
    curses.init_pair(C_I, curses.COLOR_CYAN, bg)
    curses.init_pair(C_O, curses.COLOR_YELLOW, bg)
    curses.init_pair(C_T, curses.COLOR_MAGENTA, bg)
    curses.init_pair(C_S, curses.COLOR_GREEN, bg)
    curses.init_pair(C_Z, curses.COLOR_RED, bg)
    curses.init_pair(C_J, curses.COLOR_BLUE, bg)
    curses.init_pair(C_L, curses.COLOR_WHITE, bg)
    curses.init_pair(C_TEXT, curses.COLOR_CYAN, bg)
    curses.init_pair(C_BORDER, curses.COLOR_YELLOW, bg)
    curses.init_pair(C_GHOST, curses.COLOR_WHITE, bg)


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
    base = PIECES[piece_type]
    grid = shape_to_grid(base["shape"])
    n = len(grid)
    return {
        "type": piece_type,
        "grid": grid,
        "color": base["color"],
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
                    board[br][bc] = piece["color"]


def clear_lines(board):
    kept = [row for row in board if any(cell is None for cell in row)]
    cleared = BOARD_ROWS - len(kept)
    for _ in range(cleared):
        kept.insert(0, [None] * BOARD_COLS)
    return kept, cleared


# --- Screens -------------------------------------------------------------

def title_screen(stdscr, high_score):
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    stdscr.clear()
    h, w = stdscr.getmaxyx()

    title_w = text_big_width("TETRIS")
    draw_text_big(stdscr, "TETRIS", 2, max(0, (w - title_w) // 2), C_I, curses.A_BOLD)

    lines = [
        ("RETRO TERMINAL EDITION", C_TEXT, curses.A_BOLD),
        ("", 0, 0),
        (f"HIGH SCORE: {high_score}", C_O, curses.A_BOLD),
        ("", 0, 0),
        ("ARROWS/WASD TO MOVE   UP/X ROTATE CW   Z ROTATE CCW", C_TEXT, 0),
        ("SPACE HARD DROP   P PAUSE   Q QUIT", C_TEXT, 0),
        ("", 0, 0),
        ("PRESS ANY KEY TO START", C_BORDER, curses.A_BOLD | curses.A_BLINK),
    ]
    start_y = 9
    for i, (line, color, attr) in enumerate(lines):
        safe_addstr(stdscr, start_y + i, max(0, (w - len(line)) // 2), line, color, attr)

    stdscr.refresh()
    stdscr.getch()


def draw_border(stdscr, top, left, bottom, right):
    try:
        stdscr.addch(top, left, curses.ACS_ULCORNER, curses.color_pair(C_BORDER))
        stdscr.addch(top, right, curses.ACS_URCORNER, curses.color_pair(C_BORDER))
        stdscr.addch(bottom, left, curses.ACS_LLCORNER, curses.color_pair(C_BORDER))
        stdscr.addch(bottom, right, curses.ACS_LRCORNER, curses.color_pair(C_BORDER))
        for x in range(left + 1, right):
            stdscr.addch(top, x, curses.ACS_HLINE, curses.color_pair(C_BORDER))
            stdscr.addch(bottom, x, curses.ACS_HLINE, curses.color_pair(C_BORDER))
        for y in range(top + 1, bottom):
            stdscr.addch(y, left, curses.ACS_VLINE, curses.color_pair(C_BORDER))
            stdscr.addch(y, right, curses.ACS_VLINE, curses.color_pair(C_BORDER))
    except curses.error:
        pass


def draw_preview(stdscr, top, left, piece_type):
    base = PIECES[piece_type]
    grid = shape_to_grid(base["shape"])
    color = base["color"]
    for r, row in enumerate(grid):
        for c, filled in enumerate(row):
            if filled:
                safe_addstr(stdscr, top + r, left + c * CELL_W, "[]", color, curses.A_BOLD)


def draw_game(stdscr, board, piece, next_type, score, lines, level, high_score, paused, layout):
    pf_top, pf_left, b_top, b_left, b_bottom, b_right, side_x = layout
    stdscr.erase()
    draw_border(stdscr, b_top, b_left, b_bottom, b_right)

    for r in range(BOARD_ROWS):
        for c in range(BOARD_COLS):
            color = board[r][c]
            if color is not None:
                safe_addstr(stdscr, pf_top + r, pf_left + c * CELL_W, "[]", color, curses.A_BOLD)

    if piece is not None:
        ghost_row = ghost_drop_row(board, piece)
        n = len(piece["grid"])
        for r in range(n):
            for c in range(n):
                if piece["grid"][r][c]:
                    gr, gc = ghost_row + r, piece["col"] + c
                    if 0 <= gr < BOARD_ROWS:
                        safe_addstr(stdscr, pf_top + gr, pf_left + gc * CELL_W, "::", C_GHOST, curses.A_DIM)

        for r in range(n):
            for c in range(n):
                if piece["grid"][r][c]:
                    pr, pc = piece["row"] + r, piece["col"] + c
                    if 0 <= pr < BOARD_ROWS:
                        safe_addstr(stdscr, pf_top + pr, pf_left + pc * CELL_W, "[]", piece["color"], curses.A_BOLD)

    safe_addstr(stdscr, b_top, side_x, "NEXT", C_TEXT, curses.A_BOLD)
    draw_preview(stdscr, b_top + 2, side_x, next_type)

    info_y = b_top + 7
    safe_addstr(stdscr, info_y, side_x, f"SCORE", C_TEXT, curses.A_BOLD)
    safe_addstr(stdscr, info_y + 1, side_x, f"{score}", C_O, curses.A_BOLD)
    safe_addstr(stdscr, info_y + 3, side_x, f"LINES", C_TEXT, curses.A_BOLD)
    safe_addstr(stdscr, info_y + 4, side_x, f"{lines}", C_O, curses.A_BOLD)
    safe_addstr(stdscr, info_y + 6, side_x, f"LEVEL", C_TEXT, curses.A_BOLD)
    safe_addstr(stdscr, info_y + 7, side_x, f"{level}", C_O, curses.A_BOLD)
    safe_addstr(stdscr, info_y + 9, side_x, f"HIGH", C_TEXT, curses.A_BOLD)
    safe_addstr(stdscr, info_y + 10, side_x, f"{high_score}", C_O, curses.A_BOLD)

    safe_addstr(stdscr, b_bottom - 1, side_x, "P PAUSE  Q QUIT", C_BORDER)

    if paused:
        msg = "PAUSED"
        cy = (b_top + b_bottom) // 2
        cx = pf_left + (BOARD_COLS * CELL_W) // 2 - len(msg) // 2
        safe_addstr(stdscr, cy, cx, msg, C_TEXT, curses.A_BOLD | curses.A_BLINK | curses.A_REVERSE)

    stdscr.refresh()


def game_over_screen(stdscr, score, high_score, new_record):
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    stdscr.clear()
    h, w = stdscr.getmaxyx()

    title_w = text_big_width("GAME OVER")
    draw_text_big(stdscr, "GAME OVER", 2, max(0, (w - title_w) // 2), C_Z, curses.A_BOLD)

    lines = [
        (f"SCORE: {score}", C_TEXT, curses.A_BOLD),
        ("NEW HIGH SCORE!" if new_record else f"HIGH SCORE: {high_score}",
         C_O if new_record else C_TEXT, curses.A_BOLD | (curses.A_BLINK if new_record else 0)),
        ("", 0, 0),
        ("R - PLAY AGAIN     Q - QUIT", C_BORDER, curses.A_BOLD),
    ]
    start_y = 9
    for i, (line, color, attr) in enumerate(lines):
        safe_addstr(stdscr, start_y + i, max(0, (w - len(line)) // 2), line, color, attr)
    stdscr.refresh()

    while True:
        key = stdscr.getch()
        if key in (ord("r"), ord("R")):
            return True
        if key in (ord("q"), ord("Q")):
            return False


# --- Core game loop --------------------------------------------------------

def compute_layout():
    b_top, b_left = 1, 1
    pf_top, pf_left = b_top + 1, b_left + 1
    b_bottom = pf_top + BOARD_ROWS
    b_right = pf_left + BOARD_COLS * CELL_W - 1 + 1
    side_x = b_right + 3
    return pf_top, pf_left, b_top, b_left, b_bottom, b_right, side_x


def gravity_delay_ms(level):
    return max(100, 800 - (level - 1) * 60)


def play_round(stdscr, high_score):
    layout = compute_layout()
    board = [[None] * BOARD_COLS for _ in range(BOARD_ROWS)]

    bag = draw_bag()
    bag2 = draw_bag()
    queue = bag + bag2

    piece = new_piece(queue.pop(0))
    next_type = queue[0]

    score = 0
    lines_cleared_total = 0
    level = 1
    paused = False
    game_over = False

    last_drop = time.monotonic()
    stdscr.nodelay(True)

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
        nonlocal board, score, lines_cleared_total, level
        lock_piece(board, piece)
        board, cleared = clear_lines(board)
        if cleared:
            score += LINE_SCORES.get(cleared, cleared * 200) * level
            lines_cleared_total += cleared
            level = lines_cleared_total // 10 + 1

    while True:
        draw_game(stdscr, board, piece, next_type, score, lines_cleared_total, level,
                   high_score, paused, layout)

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

        if key in (curses.KEY_LEFT, ord("a"), ord("A")):
            if valid_position(board, piece["grid"], piece["row"], piece["col"] - 1):
                piece["col"] -= 1
        elif key in (curses.KEY_RIGHT, ord("d"), ord("D")):
            if valid_position(board, piece["grid"], piece["row"], piece["col"] + 1):
                piece["col"] += 1
        elif key in (curses.KEY_UP, ord("w"), ord("W"), ord("x"), ord("X")):
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
        elif key in (curses.KEY_DOWN, ord("s"), ord("S")):
            if valid_position(board, piece["grid"], piece["row"] + 1, piece["col"]):
                piece["row"] += 1
                score += 1
                moved_this_frame = True
            else:
                lock_and_clear()
                if not spawn_next():
                    game_over = True
        elif key == ord(" "):
            drop_to = ghost_drop_row(board, piece)
            score += (drop_to - piece["row"]) * 2
            piece["row"] = drop_to
            lock_and_clear()
            if not spawn_next():
                game_over = True
            moved_this_frame = True

        if game_over:
            return score

        now = time.monotonic()
        if not moved_this_frame and (now - last_drop) * 1000 >= gravity_delay_ms(level):
            last_drop = now
            if valid_position(board, piece["grid"], piece["row"] + 1, piece["col"]):
                piece["row"] += 1
            else:
                lock_and_clear()
                if not spawn_next():
                    return score
        elif moved_this_frame:
            last_drop = now


def run(stdscr):
    curses.curs_set(0)
    init_colors()
    stdscr.keypad(True)

    high_score = load_highscore()

    while True:
        title_screen(stdscr, high_score)
        score = play_round(stdscr, high_score)

        new_record = score > high_score
        if new_record:
            high_score = score
            save_highscore(high_score)

        if not game_over_screen(stdscr, score, high_score, new_record):
            break


def main():
    rows_ok = cols_ok = True
    try:
        import shutil
        cols, rows = shutil.get_terminal_size()
        rows_ok = rows >= 24
        cols_ok = cols >= 48
    except Exception:
        pass

    if not (rows_ok and cols_ok):
        print("Your terminal is a little small for RETRO TETRIS.")
        print("Please resize it to at least 48x24 and try again.")
        return

    try:
        curses.wrapper(run)
    except KeyboardInterrupt:
        pass
    print("Thanks for playing RETRO TETRIS!")


if __name__ == "__main__":
    main()
