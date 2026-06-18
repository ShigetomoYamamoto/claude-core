# claude-config

Claude Code のグローバル設定を管理する dotfiles リポジトリ。

新しいマシンで `setup.sh` を実行するだけで、AI エージェントが自走して開発を完成させるための共通基盤が整います。

> 設計の背景や判断理由は [`docs/requirements.md`](./docs/requirements.md)（要件定義）、[`docs/architecture.md`](./docs/architecture.md)（アーキテクチャ）、[`docs/adr/`](./docs/adr/)（設計判断記録）を参照してください。

## 設計方針

**グローバル設定（このリポジトリ）** と **プロジェクト設定（`.claude/`）** で役割を分離しています。

| 層 | 場所 | 内容 |
|---|---|---|
| グローバル | `~/.claude/`（このリポジトリ） | スタック非依存・全プロジェクト共通の仕組み |
| プロジェクト | `プロジェクトルート/.claude/` | スタック固有の実装（デプロイ先・ビルドコマンド・言語別 hook） |

プロジェクト側は `/init-autonomous` を実行すると自動生成されます。

## 含まれるもの

| ディレクトリ/ファイル | 内容 |
|---|---|
| `agents/` | 15体のカスタムエージェント（architect, planner, tdd-guide, code-reviewer, requirements-analyst, deploy-runner など） |
| `commands/` | 22個のスラッシュコマンド（/requirements, /design, /plan, /tdd, /commit, /deploy, /rollback, /autorun など） |
| `hooks/` | 品質ガード・安全装置（シークレット検出・doc 生成ブロック・git 破壊操作ブロック・PR base チェック・大量削除確認） |
| `rules/` | コーディングスタイル・テスト・セキュリティ・エージェント運用ルール・Claude 使用効率化・自走/並列/メモリのループ運用ルール |
| `skills/` | 参照スキル（git-workflow, tdd-workflow, security-review） |
| `docs/` | 要件定義・アーキテクチャ・ADR |
| `settings.json.template` | Claude Code 設定テンプレート（パス自動解決・プラグイン有効化を含む） |
| `mcp.json` | MCP サーバー設定（GitHub / Playwright / Figma） |

## settings.json.template の主な設定

- `defaultMode: auto` — ほとんどの操作を自動承認
- `Bash(git *)` / `Bash(gh *)` — どのプロジェクトでも git/gh 操作が確認なしで動作
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: 1` — 複数エージェントの並列実行を有効化
- `enabledPlugins` — Slack プラグインを自動有効化
- フック: PreToolUse（doc 生成ブロック・git 破壊操作ブロック・PR base チェック・大量削除確認）、PostToolUse（シークレット検出）、Stop 音声通知

## 新しいマシンへのインストール

### 前提条件

| ツール | 最低バージョン | 備考 |
|---|---|---|
| bash | 3.2+ | macOS デフォルト |
| python3 | 3.8+ | `setup.sh` と hook 用 |
| git | 2.0+ | |
| Docker | 20.0+ | GitHub MCP 用（推奨） |

対応 OS: macOS / Linux（GUI 環境前提・Windows 非対応）

#### Docker のインストール

```bash
# macOS
brew install --cask docker
open -a Docker  # Docker Desktop を起動

# Linux
# 公式ドキュメント参照: https://docs.docker.com/engine/install/
```

#### GitHub Personal Access Token の設定

PAT は OS 標準の Keychain / Keyring に保存し、`~/.zprofile` で環境変数に展開する方式を採用します。シェル設定ファイル（dotfiles）にトークンを残さないためです。

**macOS**

```bash
security add-generic-password -a "$USER" -s "github-pat" -w "ghp_xxxx"
```

`~/.zprofile` に追記：

```bash
export GITHUB_PERSONAL_ACCESS_TOKEN="$(security find-generic-password -a "$USER" -s "github-pat" -w)"
```

**Linux（GUI 環境前提）**

```bash
sudo apt install libsecret-tools   # または sudo dnf install libsecret
secret-tool store --label="github-pat" service github-pat
```

`~/.zprofile` に追記：

```bash
export GITHUB_PERSONAL_ACCESS_TOKEN="$(secret-tool lookup service github-pat)"
```

**運用ルール**

- **Fine-grained PAT** を使い、必要なリポジトリ・スコープのみに限定する
- **有効期限を 30〜90 日** に設定して定期的にローテーションする
- `.git/config` に `username:token@` 形式で直書きしない（混入したら即除去）

### インストール

```bash
git clone https://github.com/ShigetomoYamamoto/claude-config.git ~/dotfiles/claude-config
cd ~/dotfiles/claude-config
./setup.sh
```

`setup.sh` は以下を行います：

1. **preflight check** — 必須ツール（bash・python3・git・docker）のバージョン確認
2. `agents/`, `commands/`, `hooks/`, `rules/`, `skills/` を `~/.claude/` にコピー
3. `settings.json.template` からパスを解決して `~/.claude/settings.json` を生成
4. `mcp.json` の MCP サーバー設定を `~/.claude.json` にマージ（既存設定は保持し、不足分のみ追加）

各ステップは `[1/4] ✓ ...` 形式で進捗表示します。失敗時はどのステップまで成功したかを表示します。

## 開発フロー

Claude Code は2つのモードで開発を進めます。どちらも日本語で話しかけるか、コマンドで明示的に起動できます。

### 全自動モード（要件 → デプロイまで）

```
/requirements → /design → /plan → /tdd → /commit → /create-pr → /migrate → /deploy
（要件分析）   （設計）  （計画） （テスト・実装） （コミット） （PR作成） （DB変更） （デプロイ）
```

**起動方法**
- `ユーザーのパスワードリセット機能を作って` — 日本語で要望を伝える
- `/requirements ユーザー認証機能を作りたい` — 明示的に起動

要件・設計・コミット・PR の各ステップで確認のために止まります。

### サポートモード（タスク → PR まで）

```
/analyze-task → /plan → /tdd → /commit → /create-pr → /respond-review
（タスク分析） （計画） （テスト・実装） （コミット） （PR作成） （レビュー対応）
```

**起動方法**
- `Issue #12 を実装して` — GitHub Issue を指定する
- `ログイン時のエラーメッセージが表示されないバグを直して` — 具体的なタスクを伝える
- `/analyze-task #42` — 明示的に起動

途中からでも起動できます：`/design`（設計から）、`/plan`（計画から）。

## 使い方

### パターン1: 既存プロジェクトへの導入

仕様書・設計書など必要な資料が揃っている前提です。

**ステップ1: AI エージェント自走基盤を生成**

```
/init-autonomous
```

スタックを自動検出し、以下を一括生成します：

- `.claude/settings.json` — スタック固有コマンドの権限設定（npm/pest/pytest/go/cargo など）
- `.claude/hooks/` — スタック別デバッグ出力検知（JS/TS の `console.log`・Python の `print()` など）
- `CLAUDE.md` — プロジェクトルール・エンティティ・ロール定義
- `.claude/rules/`, `.claude/commands/`, `.claude/agents/` — スタック固有の設定
- `docs/` — 仕様書テンプレート・ADR・コードマップ
- `.github/` — CI/CD・PR テンプレート・Issue テンプレート

**ステップ2: 既存資料を Claude に読み込ませる**

`/init-autonomous` の実行中に「既存の仕様書・設計書はありますか？」と聞かれます。ファイルパスを答えると Claude が内容を読み取り、`CLAUDE.md` の参照パスを自動で更新します。

以降は通常の開発フローで進めます。

---

### パターン2: 新規プロジェクト作成直後

コードも資料もほぼない状態から始めます。まず要件定義・設計を行い、その成果物を使って自走基盤を構築します。

```
# ステップ1: 要件定義
/requirements

# ステップ2: システム設計
/design

# ステップ3: AI エージェント自走基盤を生成
/init-autonomous
```

機能要件・非機能要件・データモデル・API コントラクトを定義します。承認するまで実装には進みません。

```
# ステップ4: 設計内容を docs/ に反映
docs/01_product-specifications.md  ← /requirements + /design の成果物
docs/02_detailed-design.md         ← /design の詳細設計
```

```
# ステップ5: 実装開始
/plan → /tdd → /commit → /create-pr → /migrate → /deploy
```

---

## 別マシンで最新の設定を取得するとき

```bash
cd ~/dotfiles/claude-config
git pull
./setup.sh
```

## MCP・プラグインの管理

| 種別 | 管理方法 |
|---|---|
| MCP サーバー（GitHub / Playwright / Figma） | `mcp.json` → `setup.sh` が `~/.claude.json` にマージ |
| プラグイン（Slack） | `settings.json.template` の `enabledPlugins` で自動有効化 |

新しい MCP サーバーを追加した場合は `mcp.json` に追記して `setup.sh` を再実行してください。  
新しいプラグインを有効化した場合は `settings.json.template` の `enabledPlugins` に追記してください。

## 拡張方法

新しいエージェント・コマンド・hook・MCP を追加する手順です。追加後は他マシンで `git pull && setup.sh` を実行すれば反映されます。

### 新エージェントを追加

1. `agents/<name>.md` を作成（YAML フロントマター + 英語の人格定義・300 行以内）
2. 必要なら `commands/<name>.md` を作成（日本語の薄いラッパー）
3. `rules/agents.md` のトリガー表に追記（自動起動が必要な場合）

### 新コマンドを追加

1. `commands/<name>.md` を作成（YAML フロントマター + 日本語・500 行以内）
2. 必要なら対応するエージェントを `agents/<name>.md` に作成
3. README の「使い方」セクションに記載

### 新 hook を追加

1. `hooks/<name>.py` を作成（100 行以下・単一責務）
2. `settings.json.template` の `hooks` セクションに配線追加

設計原則：

- 予期せぬエラーは `exit 0`（Claude を止めない）
- 意図的ブロックのみ `exit 2`
- ネットワーク通信禁止（ローカル処理のみ）

### 新 MCP を追加

1. `mcp.json` の `mcpServers` に追記
2. README の前提条件セクションに必要なツールを追記
