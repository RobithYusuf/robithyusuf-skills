#!/bin/sh
# Buat skill baru dari template.
#   sh scripts/new-skill.sh nama-skill
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
NAME=$1

if ! printf '%s' "$NAME" | grep -Eq '^[a-z0-9]+(-[a-z0-9]+)*$'; then
  echo "Pemakaian: sh scripts/new-skill.sh nama-skill  (huruf kecil, angka, tanda '-')" >&2
  exit 2
fi
DEST="$ROOT/skills/$NAME"
if [ -e "$DEST" ]; then
  echo "Sudah ada: skills/$NAME" >&2
  exit 1
fi

mkdir -p "$DEST"
sed "s/^name: nama-skill$/name: $NAME/" \
  "$ROOT/skills/creating-agent-skills/assets/SKILL.template.md" > "$DEST/SKILL.md"
echo "Dibuat: skills/$NAME/SKILL.md"
echo "Isi description & isi skill, lalu jalankan: sh scripts/check.sh"
