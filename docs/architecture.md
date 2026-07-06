# claude-config アーキテクチャ

## 概要

claude-config は Claude Code のグローバル設定を管理する dotfiles リポジトリ。「人間の開発業務を Claude Code が肩代わり・サポートする」という上位目的を実現するための土台・基盤を提供する。

詳細な要件は [`requirements.md`](./requirements.md) を参照。

---

## 5レイヤー構造

```
┌────────────────────────────────────────────────────────────┐
│                  claude-config（このリポジトリ）             │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Layer 1: Behavior（ふるまいの定義）                  │    │
│  │   rules/   — 不変ルール（英語）                       │    │
│  │   skills/  — 再利用可能な参照知識                     │    │
│  └────────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Layer 2: Workforce（実行者）                         │    │
│  │   agents/    — 専門役の人格定義（英語）               │    │
│  │   commands/  — スラッシュコマンド（日本語）           │    │
│  └────────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Layer 2.5: Orchestration（自走の連結）               │    │
│  │   docs/autorun-flow.md — 関門付きフロー定義          │    │
│  │   workflows/ — 大規模オーケストレーション(large-A)    │    │
│  └────────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Layer 3: Guardrails（受動的な強制）                  │    │
│  │   hooks/    — PreToolUse / PostToolUse / Stop        │    │
│  └────────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Layer 4: Wiring（接続設定）                          │    │
│  │   settings.json.template — Claude Code 本体設定      │    │
│  │   mcp.json               — 外部ツール接続            │    │
│  └────────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Layer 5: Installer                                   │    │
│  │   install.py — 本体（symlink + 構造マージ）            │    │
│  │   setup.sh   — install.py を呼ぶ薄いラッパー           │    │
│  └────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────┘
                       │ ./setup.sh → install.py
                            ▼
┌────────────────────────────────────────────────────────────┐
│                     ~/.claude/                              │
│  agents/ commands/ rules/ skills/ hooks/ workflows/ templates/ settings.json │
└────────────────────────────────────────────────────────────┘
                            │ /init-autonomous（プロジェクト内）
                            ▼
┌────────────────────────────────────────────────────────────┐
│              <project>/.claude/                             │
│  プロジェクト固有 rules / commands / agents                 │
│  + docs/ + .github/ + CLAUDE.md                             │
└────────────────────────────────────────────────────────────┘
```

---

## 各レイヤーの責務

### Layer 1: Behavior

| ディレクトリ | 責務 | 対象読者 | 言語 |
|---|---|---|---|
| `rules/` | 不変の振る舞いルール。エージェントが必ず守るべき制約 | エージェント（自動参照） | 英語 |
| `skills/` | 再利用可能な参照知識（パターン・サンプル・コマンド例） | エージェント（必要時に参照） | 英語 |

**境界:**
- `rules/` = 「MUST / NEVER / ALWAYS」を含む規範的記述
- `skills/` = 「HOW TO（手順・サンプル）」中心の参照資料
- 同じ内容を両方に書かない。`rules/` から `skills/` を参照する形に統一

### Layer 2: Workforce

| ディレクトリ | 責務 | 起動方法 | 言語 |
|---|---|---|---|
| `agents/` | 専門役の人格定義（architect / planner / tdd-guide ほか） | Claude が自動 or commands から起動 | 英語 |
| `commands/` | ユーザーが起動するスラッシュコマンド | ユーザーが `/コマンド` で起動 | 日本語 |

**設計原則:**
- 1 コマンド = 1 つの主要エージェントへの委譲（薄いオーケストレーション層）
- agents は単独で機能するように自己完結する記述
- commands は agents への入力整形と前提条件チェックに集中する

### Layer 2.5: Orchestration

| ファイル | 責務 |
|---|---|
| `docs/autorun-flow.md` | 関門付き自走のフロー定義（モード表・遷移表・関門4点・success_test）。`/autorun` が解釈する |
| `workflows/loop-engineering-large-A.js` | 大規模A の決定的オーケストレーション（plan→赤確認→実装→検証）。レビュー往復は `/review-loop` に委譲 |

**設計原則:**
- フロー定義（`autorun-flow.md`）・インタープリタ（`commands/autorun.md`）・実行部品（既存コマンド/スキル）の3層分離（ADR-008）
- 関門4点（要件確定・設計確定・PR作成・デプロイ）以外は自動連結（ADR-007）
- 安全規律の正本は `rules/loop-safety.md`

### Layer 3: Guardrails

| hook | タイミング | 責務 |
|---|---|---|
| `protected-branch-edit-guard.py` | PreToolUse(Edit / Write / MultiEdit) | 保護ブランチ（main/master/develop）上での編集を阻止 |
| `doc-blocker.py` | PreToolUse(Write) | 許可リスト外の `.md` / `.txt` 新規作成を阻止 |
| `secret-detection.py` | PostToolUse(Edit / Write / MultiEdit) | API キー・PAT・JWT のハードコード検出 |
| `git-destructive-blocker.py` | PreToolUse(Bash) | `git push --force` / `reset --hard` / `clean -fd` を防止 |
| `pr-base-checker.py` | PreToolUse(Bash) | `gh pr create` の base が `develop` 以外でブロック |
| `mass-delete-blocker.py` | PreToolUse(Bash) | `rm -rf` / 大量ファイル削除を確認 |

**設計原則:**
- フックは「Claude が忘れたときの保険」
- 単一責務（1 ファイル 1 検査）
- 予期せぬエラーは `exit 0` で Claude を止めない
- 意図的なブロック（doc-blocker など）のみ `exit 2`
- ネットワーク通信禁止・ローカル処理のみ
- 上限 100 行

### Layer 4: Wiring

| ファイル | 責務 |
|---|---|
| `settings.json.template` | Claude Code 本体設定（permissions・hooks 配線・enabledPlugins）。`model` 等の個人設定は持たない |
| `mcp.json` | MCP サーバー定義（GitHub / Playwright / Figma） |

**設計原則:**
- `settings.json.template` は人がレビュー可能な単一の真実の源
- `__HOME__` のような Templating はパス系のみ
- `mcp.json` のマージは追加のみ。既存キーは保護

### Layer 5: Installer

`install.py`（`setup.sh` はこれを呼ぶ薄いラッパー）の責務:

1. 必須ツールの事前検証（preflight check）
2. 静的ディレクトリ（agents/commands/rules/skills/hooks/workflows/templates）の **symlink 化**（repo を編集すれば即 live に反映。実体ディレクトリは `~/.claude/.backup/` に退避してからリンク）
3. `settings.json` の **構造マージ**（`__HOME__` 置換 → FORCE/DEFAULT の2規則でキー単位マージ。live のキーは決して削除しない）
4. `mcp.json` のマージ（Python による既存保護つき追加マージ）

**設計原則:**
- 静的部分は symlink なので repo が単一の真実の源（`git pull` で即反映）
- `settings.json` は実行時に Claude 自身が書くため上書きせずマージ（個人設定・通知を保護）
- 破壊的操作の前に必ずバックアップ。`--dry-run` で書き込みなしの事前確認が可能
- すべての操作を idempotent に保ち、何を書いたかを stdout で逐次表示

> 採用方式の変遷は ADR-004（コピー型・superseded）→ ADR-009（symlink + 構造マージ）を参照。

---

## 2層境界（グローバル / プロジェクト）

| 層 | 場所 | 内容 |
|---|---|---|
| グローバル | `~/.claude/`（このリポジトリ） | スタック非依存・全プロジェクト共通の仕組み |
| プロジェクト | `<project>/.claude/` | スタック固有の実装（デプロイ先・ビルドコマンド・言語別 hook） |

**プロジェクト側は `/init-autonomous` で生成される。** スタック自動検出後、検出言語に応じた hook（デバッグ出力検知など）を生成する。

---

## 拡張ポイント

### 新しいマシンへの対応

```bash
git clone <repo> ~/dotfiles/claude-config
cd ~/dotfiles/claude-config
./setup.sh
# 起動後、`GITHUB_PERSONAL_ACCESS_TOKEN`（Keychain→zprofile）を設定し、
# Claude Code 内で `/plugin` から公式 `github` プラグインを導入
```

### 新エージェントを追加

1. `agents/<name>.md` を作成（YAML フロントマター + 英語の人格定義）
2. 必要なら `commands/<name>.md` を作成（日本語の薄いラッパー）
3. `rules/agents.md` のトリガー表に追記（自動起動が必要な場合）
4. コミット → 他マシンで `git pull`（agents/ は symlink なので即反映）

### 新コマンドを追加

1. `commands/<name>.md` を作成（YAML フロントマター + 日本語）
2. 必要なら対応するエージェントを `agents/<name>.md` に作成
3. README の「使い方」セクションに記載
4. コミット → 他マシンで `git pull`（commands/ は symlink なので即反映）

### 新 hook を追加

1. `hooks/<name>.py` を作成（100 行以下・単一責務）
2. `settings.json.template` の `hooks` セクションに配線追加
3. コミット → 他マシンで `git pull && ./setup.sh`（settings.json.template の配線変更を反映するため再実行が必要）

### 新 MCP を追加

1. `mcp.json` の `mcpServers` に追記
2. README の前提条件セクションに必要なツールを追記
3. コミット → 他マシンで `git pull && setup.sh`（既存設定は壊さない）

---

## エラーハンドリング戦略

| 失敗パターン | 期待動作 |
|---|---|
| Python3 が見つからない | `setup.sh` ラッパーの `exec python3` がシェルエラーで停止（install.py 本体が起動できないため）。3.8 未満は install.py の preflight が検知して停止 |
| `~/.claude.json` が JSON として壊れている | マージを中止、エラー表示。既存ファイルは触らない |
| hook 内 Python の予期せぬ例外 | exit 0 で Claude を止めない |
| GitHub MCP 未認証 | install.py は関与しない。公式 `github` プラグイン未導入、または `GITHUB_PERSONAL_ACCESS_TOKEN` 未設定の間は GitHub ツールが使えない |
| MCP マージ時の同名キー衝突 | 既存値を尊重し追加しない |
