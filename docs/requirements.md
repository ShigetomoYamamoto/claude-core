# claude-core 要件定義

> **本リポジトリは claude-core foundation（ドメイン中立の正本）です（[ADR-023](./adr/023-three-foundation-split.md)）。**
> 単一設定を core / engineering / work-agent の3 foundation に分割した結果、この要件定義は
> **claude-core が実際に所有する範囲だけ**を記述します。開発ワークフロー（要件→設計→実装→
> レビュー→PR→デプロイ、TDD、自走ループ等）の要件は **claude-engineering**、業務/運用
> ワークフローの要件は **claude-work-agent** が各 foundation 側で所有します。分割前
> （single-repo）の全体要件は git 履歴と [ADR-023](./adr/023-three-foundation-split.md) に
> 保存済みのため、本ファイルからは再掲しません。資産の分類は
> [`docs/migration/inventory.md`](./migration/inventory.md) を参照。

## 1. 上位目的

claude-core は、Claude Code をどのプロジェクト・どのドメインで使うときも共通して効く
**ドメイン中立の振る舞い規範と安全装置**を、グローバル `~/.claude` に提供する土台である。
engineering / work-agent はこの土台の上に、それぞれのドメイン固有ワークフローをプロジェクト
ローカルに載せる（1プロジェクト=1ドメイン）。core 自身は開発フローも業務フローも持たず、
「常時ロードされる最小・中立の核」に徹する。ドメイン固有の資産（コマンド・エージェント・
スタック統合・MCP・資格情報）は一切持たない。

## 2. 機能要件

### A. ドメイン中立の振る舞い規範（rules）
毎セッション常時ロードされる、スタック非依存の規範を提供する。

| ルール | 内容 |
|---|---|
| `answer-only.md` | 明示依頼まで read-only（投機的な変更をしない） |
| `collaboration-style.md` | 批判的な相談相手としての振る舞い・回答の形・言語方針 |
| `claude-efficiency.md` | モデル選択（thinking tier と Sonnet/Haiku の役割分担の前提） |
| `memory.md` | アウターループ学習（何を永続化するか） |
| `role-separation.md` | 思考ティアは思考・Sonnet/Haiku は実行。main-loop-execution-guard で強制 |
| `safety-irreversible.md` | 不可逆・外向き操作は人間確認、有界な自走、maker≠checker |
| `secret-hygiene.md` | 秘密情報の基本衛生（環境変数/keychain・.gitignore） |

### B. ドメイン中立の安全装置（hooks）
「Claude が規範を忘れたときの保険」となるローカル hook を提供する。

| hook | タイミング | 役割 |
|---|---|---|
| `main-loop-execution-guard.py` | PreToolUse(Edit系/Bash) | 思考ティアの編集・変更系 Bash をブロック |
| `doc-blocker.py` | PreToolUse(Write) | 許可外の新規 .md/.txt 生成を阻止 |
| `mass-delete-blocker.py` | PreToolUse(Bash) | 再帰/大量削除を確認、ルート/システムは決定的ブロック |
| `git-add-secret-blocker.py` | PreToolUse(Bash) | 秘匿ファイルの `git add` をブロック |
| `secret-detection.py` | PostToolUse(Edit系) | ハードコード秘密を検出して警告（非ブロック） |

### C. ドメイン中立のスキル（skills）

| skill | 内容 |
|---|---|
| `3-line-contract` | 着手前の3行タスク整形（中立） |
| `memory-dream` | ナレッジベース棚卸し（中立） |

### D. copy 型インストーラとマルチマシン同期
- `installer.py` + `install.py` が `rules/` `hooks/` `skills/` を `~/.claude` へ**コピー**する（symlink 廃止）。
- `<target>/.claude-core.manifest.json`（管理ファイル一覧 + sha256）が所有境界。install/update/uninstall/verify は manifest 内かつハッシュ一致のファイルのみ扱い、未知・ローカル改変ファイルは触らない。
- `settings-fragment.json` を `settings.json` へキー単位マージ（`__TARGET__` を実パス解決。live キー・他 foundation の配線を壊さない）。
- `--dry-run`・衝突検出・backup・冪等 update を備える。
- copy 型のため、repo 更新の live 反映には対象マシンで `python3 install.py`（update）の再実行が必要。

### 対象外（他 foundation / プロジェクトローカル）
- 開発ワークフロー一式（コマンド・エージェント・TDD・自走ループ・開発 git hook）→ **claude-engineering**
- 業務/運用ワークフロー → **claude-work-agent**
- グローバル MCP・開発/業務プラグインのグローバル有効化・資格情報・ワークスペース ID・スタック統合 → プロジェクトローカル（core は持たない）

## 3. 非機能要件

### 信頼性

| 項目 | 内容 |
|---|---|
| `install.py` 失敗時 | 即停止し、どのステップまで成功したかを表示 |
| settings.json マージ | キー単位追加方式。壊れた JSON のときは触れず警告のみ（live 保護） |
| hook の予期せぬエラー | `exit 0` で Claude を止めない（[ADR-006](./adr/006-hook-error-policy.md)） |
| 意図的ブロック | 該当 hook のみ `exit 2`（secret-detection は検出のみで exit 2 なし） |

### 移植性

| 項目 | 内容 |
|---|---|
| 対応 OS | macOS / Linux（Windows 非対応） |
| 必須ツール | Python 3.8+ / git 2.0+ |

### セキュリティ

| 項目 | 内容 |
|---|---|
| 秘密混入防止 | `.gitignore` + `secret-detection.py` / `git-add-secret-blocker.py` |
| 秘密の非保存 | memory・ログ・ドキュメントに秘密を書かない（`secret-hygiene.md`） |
| hook の外部通信 | 禁止（ローカル処理のみ） |

### 保守性

| 項目 | 内容 |
|---|---|
| ファイルサイズ上限 | rules 200行 / skills 300行 / hooks 100行 |
| 1ファイル1責務 | 明文化 |
| 重複禁止 | 同じ情報は1箇所へ集約。rules は常時ロード＝行数がコンテキストコスト（[ADR-022](./adr/022-autorun-flow-out-of-always-loaded-rules.md)） |

### 観測性

| 項目 | 内容 |
|---|---|
| `install.py` ログ | ステップごとの変更内容を表示（`--dry-run` で事前確認） |
| hook 警告 | 標準エラーへ簡潔に |

## 4. 受け入れ基準

形式的なテストシナリオは作らない。日々の運用で気づいた不足・違和感を GitHub Issue として記録し、随時調整する。インストーラの単体テストは `tests/` が担保する。

## 5. 制約・前提条件

| 項目 | 内容 |
|---|---|
| 必須ツール | Python 3.8+ / git 2.0+ |
| 対応 OS | macOS / Linux（Windows 非対応） |
| Claude Code 規約 | `~/.claude/` ディレクトリ構造に準拠 |
| 言語 | ドキュメント・コミット description は日本語（[ADR-003](./adr/003-language-policy.md) / [ADR-021](./adr/021-language-policy-update.md)）。rules は英語 |
| 利用形態 | 個人利用（将来チーム化を想定） |
