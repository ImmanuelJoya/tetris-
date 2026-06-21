# RETRO TETRIS — Terminal Edition

A classic falling-blocks game with a retro arcade look, playable entirely
in your terminal. Pure Python standard library — no dependencies, no
internet connection needed to play.

## Install

1. Download `retrotetris.py` and `install.sh` into the same folder.
2. In that folder, run:

   ```bash
   chmod +x install.sh
   ./install.sh
   ```

3. Start playing:

   ```bash
   retrotetris
   ```

If `install.sh` warns that `~/.local/bin` isn't on your `PATH`, follow the
one-line fix it prints, then reopen your terminal.

### Prefer not to install anything?

Just run it directly, no install step needed:

```bash
python3 retrotetris.py
```

### Windows users

The `curses` library isn't built into Windows Python. Install the
community package first:

```bash
pip install windows-curses
```

Then run `python retrotetris.py` from PowerShell, Command Prompt, or
Windows Terminal.

## Controls

| Key                  | Action              |
|-----------------------|--------------------|
| Left/Right or A/D     | Move                |
| Down or S              | Soft drop           |
| Up/W or X              | Rotate clockwise    |
| Z                       | Rotate counter-clockwise |
| Space                   | Hard drop           |
| P                        | Pause / Resume      |
| Q                        | Quit                |
| R                        | Play again (on game over screen) |

## Features

- 7 standard tetromino pieces with a fair "bag" randomizer (no long
  unlucky droughts of one piece)
- Ghost piece preview showing where your piece will land
- Next-piece preview
- Increasing speed as you level up
- High score saved to `~/.retrotetris_highscore` and persists between
  sessions

## Notes

Your terminal window should be at least 48 columns × 24 rows. If it's
too small, the game will tell you and exit gracefully rather than
rendering incorrectly.

## Uninstall

```bash
rm ~/.local/bin/retrotetris
rm ~/.retrotetris_highscore   # optional, clears your high score
```
