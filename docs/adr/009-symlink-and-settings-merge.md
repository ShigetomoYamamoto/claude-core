# ADR-009: インストーラは symlink + settings.json 構造マージ（コピー型を置換）

**ステータス**: accepted

**日付**: 2026-06-19

**置き換え対象**: [ADR-004](004-copy-based-setup.md)（コピー型）

## コンテキスト

ADR-004 で採用したコピー型インストーラ（`rm -rf` + `cp -r`、`settings.json` は template から sed で生成して丸ごと上書き）に、運用上の実害が2つ顕在化した:

1. **ユーザー設定の無断削除** — `~/.claude/<dir>` を確認なしで `rm -rf` するため、ユーザーがそこに置いた実体ファイルが消える（GitHub 上でも指摘あり）。
2. **`settings.json` の上書きによる消失** — `settings.json` は Claude Code 自身が実行時に書き込む（`/effort`・`/model`・プラグイン ON/OFF・「常に許可」権限・通知設定）。template で丸ごと上書きすると、これらが消える。実際に通知設定が消える事故が発生した。

ADR-004 が当時 symlink を退けた理由は「`__HOME__` 置換ができない」「`mcp.json` の部分マージができない」だったが、これは **「静的ディレクトリ＝symlink」「`settings.json`＝マージ」と性質ごとに分ければ両立する** と分かった。

## 検討した選択肢

1. **加算マージのみ（不足キーだけ追加）** — 破壊はしないが、repo 側の hook/権限更新が既存マシンに伝播しない。
2. **managed/local の物理2ファイル分離（`settings.local.json`）** — Claude は実行時設定を `settings.json` 側に書くため、分離しても上書き消失は防げない。
3. **symlink + `settings.json` 構造マージ（採用）** — 静的部分は symlink で即反映、`settings.json` はキー単位マージ。
4. **chezmoi 等の専用ツール** — 高機能だが外部依存が増える。今回の規模には過剰。
5. **Claude Code プラグイン形式** — ネイティブだが大規模リファクタ。将来課題として分離。

実装言語も、コピー型は JSON マージのため既に python へ escape しており、bash 本体に残るのは危険な `rm -rf`/`cp` のみだった。よって **インストーラ本体を `install.py`（Python）に移し、`setup.sh` は後方互換の薄いラッパー** とする。

## 決定

**symlink + `settings.json` 構造マージを採用する。**

- **静的ディレクトリ**（agents/commands/rules/skills/hooks/workflows/templates）は repo への **symlink**。`git pull` で即 live。実体ディレクトリがあれば `~/.claude/.backup/<timestamp>/` に退避してからリンク化。
- **`settings.json`** は2規則でキー単位マージ（live のキーは決して削除しない）:
  - **FORCE**（repo が勝つ＝配線が伝播）: `hooks.PreToolUse` / `PostToolUse`、`permissions.allow`（和集合）、`env`、`enabledPlugins`、`extraKnownMarketplaces`。template を空にすれば明示的に削除でき、template が無言ならその live キーは保持。
  - **DEFAULT**（live に無い時だけ補充。live に値があれば常に live が勝つ）: それ以外（通知 hook・`model`・`effortLevel` など）。
- **`mcp.json`** は従来どおり `~/.claude.json` への追加マージ（既存保護）。
- 破壊的操作の前に必ずバックアップ。`--dry-run` で書き込みなしの事前確認を提供。
- repo の配置場所は固定（移動・削除すると symlink が切れる）前提。

## 結果

### Positive

- `~/.claude` のユーザー設定・通知を破壊しない（事故の根本原因を構造的に解消）。
- repo の hook/権限/エージェント編集が `git pull` だけで全マシンに即反映（再 `setup.sh` 不要）。
- `settings.json` の配線更新（新 blocker 等）は伝播しつつ、実行時の個人設定は保持。
- `--dry-run`・バックアップにより安全に適用可能。

### Negative

- repo を移動・削除すると symlink が切れる（コピー型の独立性は失われる）。固定運用が前提。
- マージ規則を理解しないと「なぜこのキーは更新され、あのキーは保持されるのか」が非自明（README / docstring に明記して緩和）。
- `__HOME__` 置換が必要な `settings.json` は symlink にできず、引き続きマージ生成が必要。

## 関連

- 置換対象: ADR-004（コピー型）
- 実装: `install.py`・`setup.sh`（ラッパー）・`settings.json.template`
- アーキテクチャ: `docs/architecture.md` Layer 5: Installer
- 要件定義: `docs/requirements.md` セクション「E. マルチマシン同期」
