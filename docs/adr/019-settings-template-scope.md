# ADR-019: settings.json.template のスコープは FORCE 配線のみ（個人・DEFAULT キーは ~/.claude 側）

**ステータス**: accepted（settings.json.template へ反映済み。2026-07-04 にステータス更新）

**日付**: 2026-06-24

## コンテキスト

[ADR-009](./009-symlink-and-settings-merge.md) で `settings.json` は「テンプレート → install.py がキー単位マージ（FORCE=repo が伝播 / DEFAULT=live 優先）」方式を採用した。しかし `settings.json.template` が FORCE/DEFAULT の区別に従わず、個人・実行時キー（通知音 hook=afplay、effortLevel、各種 toggle）まで抱えていたため、live(`~/.claude/settings.json`) との恒常的ドリフト（afplay↔say、high↔xhigh）が生じ、「どのキーが伝播し、どれが保持されるか」が非自明になっていた（ADR-009 Negative の顕在化）。

設定ファイルの管理境界を一般化すると:

- **A. Repo 正本＋symlink** — 不変・ツールは読むだけ・機密なし（agents/commands/hooks/rules/skills/workflows/templates）。
- **B. ハイブリッド（テンプレ→マージ）** — 共有基盤はあるがツールが書く／`__HOME__` 置換が要る（settings.json, mcp.json）。
- **C. ~/.claude のみ** — ツールが書く／マシン等で可変／機密／純ランタイム。

B の settings は「キー単位」で A 寄り（FORCE 配線）と C 寄り（個人・DEFAULT）に分かれる。テンプレに C 寄りキーを置くと混乱の元になる。

## 検討した選択肢

1. **方針を文書化のみ** — テンプレは触らず README/ADR に線引きだけ記す。ドリフトは残る。
2. **テンプレを FORCE 配線のみに純化（採用）** — 個人・DEFAULT キーをテンプレから外し、FORCE キーを現状 baseline に正本化。
3. **settings を完全 symlink 化** — ツールが実行時に書き込む＋`__HOME__` 置換のため不可（ADR-009 で却下済み）。

## 決定

**`settings.json.template` には FORCE（全マシンに伝播させる安全・振る舞いの配線）キーのみを置く。個人・実行時（DEFAULT）キーはテンプレに置かず `~/.claude/settings.json` 側にのみ存在させる。**

- **テンプレに残す（FORCE）**: `env` / `permissions`(allow+defaultMode) / `hooks.PreToolUse` / `hooks.PostToolUse`（安全ガード群）/ `enabledPlugins` / `extraKnownMarketplaces`。
- **テンプレから外す（個人・DEFAULT・~/.claude 側）**: `hooks.Stop` / `hooks.PermissionRequest` / `hooks.Notification`（通知音・音声＝好み）、`effortLevel`、`remoteControlAtStartup`、`agentPushNotifEnabled`、`skipAutoPermissionPrompt`。
- `enabledPlugins` は現行 baseline に合わせ `github` / `frontend-design` を追記（正本化）。

ADR-009 のマージ規則（FORCE/DEFAULT）は不変。本 ADR はその規則に「テンプレの内容を従わせる」スコープ確定である。既存マシンの live キーは DEFAULT マージで保持されるため破壊はない（テンプレから DEFAULT キーを外しても live は消えない）。

## 結果

### Positive

- テンプレ＝「全マシン共通の安全・配線の正本」に純化し、ドリフトと非自明さが解消。
- 「安全/振る舞い配線 → テンプレ（伝播）」「個人/実行時 → ~/.claude」の明確な境界。

### Negative

- 新規マシンは個人キー（通知音・effort 等）の seed を持たず、Claude Code 既定＋手動設定になる（既存マシンは影響なし）。
- `enabledPlugins` は FORCE のため、プラグインを増減したらテンプレ更新が要る（正本化の対価）。

## 関連

- [ADR-009](./009-symlink-and-settings-merge.md) — symlink + settings マージ（本 ADR はそのテンプレ内容のスコープを確定）
- [ADR-004](./004-copy-based-setup.md) — 置換されたコピー型
- `settings.json.template` / `install.py` — 実装
