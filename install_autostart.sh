#!/bin/sh

set -eu

APP_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
AUTOSTART_DIR="${XDG_CONFIG_HOME:-${HOME}/.config}/autostart"
DESKTOP_TEMPLATE="$APP_DIR/picam-2-gui.desktop"
DESKTOP_FILE="$AUTOSTART_DIR/picam-2-gui.desktop"

mkdir -p "$AUTOSTART_DIR"

escaped_app_dir=$(printf '%s' "$APP_DIR" | sed 's/[&|\\]/\\&/g')
temporary_desktop_file=$(mktemp)
trap 'rm -f "$temporary_desktop_file"' EXIT
sed "s|__APP_DIR__|$escaped_app_dir|g" "$DESKTOP_TEMPLATE" > "$temporary_desktop_file"

chmod +x "$APP_DIR/launcher.sh"
if [ -w "$AUTOSTART_DIR" ]; then
	install -m 644 "$temporary_desktop_file" "$DESKTOP_FILE"
else
	sudo install -d "$AUTOSTART_DIR"
	sudo install -m 644 "$temporary_desktop_file" "$DESKTOP_FILE"
fi

printf 'Installed %s\n' "$DESKTOP_FILE"
