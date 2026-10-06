#!/bin/sh
# Pasang semua skill di repo ini ke agent lokal lewat symlink,
# sehingga perubahan di repo langsung terpakai tanpa instal ulang.
#   sh scripts/install-local.sh                 # ~/.claude/skills
#   sh scripts/install-local.sh ~/.codex/skills # folder skill agent lain
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
TARGET=${1:-$HOME/.claude/skills}
mkdir -p "$TARGET"

for dir in "$ROOT"/skills/*/; do
  name=$(basename "$dir")
  link="$TARGET/$name"
  if [ -e "$link" ] && [ ! -L "$link" ]; then
    echo "Lewati $name: $link sudah ada dan bukan symlink (tidak ditimpa)"
    continue
  fi
  ln -sfn "${dir%/}" "$link"
  echo "Terpasang: $link"
done
