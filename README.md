# RETRO TETRIS — Dark Terminal Edition

A multi-panel Tetris TUI for your terminal, forced to a dark color scheme
regardless of your terminal's theme. Pure Python standard library on
Mac/Linux — no dependencies. Windows needs one extra package (below).

## Install

### Option A — straight from GitHub (no PyPI account needed)

```bash
pip install git+https://github.com/ImmanuelJoya/tetris-.git
```

### Option B — from PyPI (once published)

```bash
pip install retrotetris
```

Either way, this installs a `tetris` command on your PATH.

### Windows

`curses` isn't built into Windows Python, so install the community
package first — `pyproject.toml` already lists it as a Windows-only
dependency, so a plain `pip install` (Option A or B above) pulls it in
automatically. If you ever need it manually:

```powershell
pip install windows-curses
```

## Play

```bash
tetris
```

## Controls

| Key                  | Action                    |
|-----------------------|---------------------------|
| H / Left / A           | Move left                 |
| L / Right / D          | Move right                |
| J / Down / S           | Soft drop                 |
| K / Up / W / X         | Rotate clockwise          |
| Z                      | Rotate counter-clockwise  |
| Space                  | Hard drop                 |
| P                      | Pause / Resume            |
| Q                      | Quit                      |

## Features

- 7 standard tetrominoes with a fair "bag" randomizer
- Ghost piece showing where the current piece will land
- Stats / Next / Help panels in a bordered, dark-themed layout
- Selectable starting level (0–9) with speed that increases as you clear lines
- High score saved to `~/.retrotetris_highscore`, persists between sessions

## Requirements

- Python 3.8+
- A terminal at least 72 columns × 24 rows (it'll tell you if yours is
  too small)

## Uninstall

```bash
pip uninstall retrotetris
rm ~/.retrotetris_highscore   # optional, clears your high score
```

## Publishing to PyPI (maintainer notes)

```bash
python -m pip install --upgrade build twine
python -m build
twine upload dist/*
```

Requires a free PyPI account and an API token (https://pypi.org/account/register/).
