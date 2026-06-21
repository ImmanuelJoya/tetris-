#!/usr/bin/env bash
# Installer for RETRO TETRIS
set -e

INSTALL_DIR="$HOME/.local/bin"
COMMAND_NAME="retrotetris"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_FILE="$SCRIPT_DIR/retrotetris.py"

if [ ! -f "$SOURCE_FILE" ]; then
    echo "Error: retrotetris.py not found next to install.sh"
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 is required but was not found on your PATH."
    exit 1
fi

mkdir -p "$INSTALL_DIR"
cp "$SOURCE_FILE" "$INSTALL_DIR/$COMMAND_NAME"
chmod +x "$INSTALL_DIR/$COMMAND_NAME"

echo "RETRO TETRIS installed to $INSTALL_DIR/$COMMAND_NAME"

case ":$PATH:" in
    *":$INSTALL_DIR:"*)
        echo ""
        echo "Run it with:  $COMMAND_NAME"
        ;;
    *)
        echo ""
        echo "NOTE: $INSTALL_DIR is not on your PATH yet."
        echo "Add this line to your ~/.bashrc or ~/.zshrc:"
        echo ""
        echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
        echo ""
        echo "Then restart your terminal (or run 'source ~/.bashrc') and type:"
        echo "    $COMMAND_NAME"
        ;;
esac
