# Aturan agent

File di folder ini adalah instruksi tetap (memori) untuk agent. Bedanya dengan skill: aturan **selalu** dimuat di setiap sesi, sedangkan skill hanya dimuat saat relevan. Jadi isinya harus pendek, berupa preferensi kerja, bukan prosedur panjang.

| File | Isi |
|---|---|
| `AGENTS.global.md` | Gaya bahasa, kata kunci, cara kerja, format laporan, konvensi. Berlaku untuk semua proyek. |

Template `AGENTS.md` per proyek ada di [`../skills/writing-agents-md/assets/AGENTS.template.md`](../skills/writing-agents-md/assets/AGENTS.template.md). Skill [`writing-agents-md`](../skills/writing-agents-md/SKILL.md) bisa mengisinya otomatis dari isi repo.

## Memasang aturan global

Pakai symlink supaya satu sumber dipakai semua agent. Cadangkan dulu file lama bila sudah ada.

```bash
REPO=~/Projects/robithyusuf-skills
ln -sf "$REPO/rules/AGENTS.global.md" ~/.claude/CLAUDE.md     # Claude Code
ln -sf "$REPO/rules/AGENTS.global.md" ~/.codex/AGENTS.md      # Codex CLI
ln -sf "$REPO/rules/AGENTS.global.md" ~/.gemini/GEMINI.md     # Gemini CLI
```

Di Windows (PowerShell sebagai admin):

```powershell
New-Item -ItemType SymbolicLink -Path "$HOME\.claude\CLAUDE.md" -Target "C:\path\robithyusuf-skills\rules\AGENTS.global.md"
```

Bagian **Lingkungan** berbeda per mesin. Sunting sesuai mesin yang dipakai, atau pindahkan ke file lokal yang tidak di-commit.
