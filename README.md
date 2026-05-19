# claude-config

Claude Code のグローバル設定を管理する dotfiles リポジトリ。

新しいマシンで `setup.sh` を実行するだけで、AI エージェントが自走して開発を完成させるための共通基盤が整います。

## 設計方針

**グローバル設定（このリポジトリ）** と **プロジェクト設定（`.claude/`）** で役割を分離しています。

| 層 | 場所 | 内容 |
|---|---|---|
| グローバル | `~/.claude/`（このリポジトリ） | git・gh 操作、品質ガード、汎用エージェント |
| プロジェクト | `プロジェクトルート/.claude/` | スタック固有コマンド、ドメイン知識、CI設定 |

プロジェクト側は `/init-autonomous` を実行すると自動生成されます。

## 含まれるもの

| ディレクトリ/ファイル | 内容 |
|---|---|
| `agents/` | 9体のカスタムエージェント（planner, tdd-guide, code-reviewer, security-reviewer など） |
| `commands/` | スラッシュコマンド（/design, /plan, /tdd, /commit, /create-pr, /init-autonomous など） |
| `hooks/` | 品質ガードフック（console.log 警告・シークレット検出・セッション終了監査） |
| `rules/` | コーディングスタイル、テスト要件、セキュリティ、エージェント運用ガイドライン |
| `skills/` | 参照ドキュメント（フロントエンド/バックエンドパターン、git-workflow など） |
| `settings.json.template` | Claude Code 設定テンプレート（インストール時にパス自動解決） |

## settings.json.template の主な設定

- `defaultMode: auto` — ほとんどの操作を自動承認
- `Bash(git *)` / `Bash(gh *)` — どのプロジェクトでも git/gh 操作が確認なしで動作
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: 1` — 複数エージェントの並列実行を有効化
- フック: Stop 時に音声通知（macOS: afplay / Linux: terminal bell）+ console.log 監査

## 新しいマシンへのインストール

### 前提条件

このリポジトリは **Docker 必須** の構成です。GitHub MCP を Docker コンテナで起動することで、PAT を平文設定ファイル（`~/.claude.json` 等）に書き残さない設計にしています。

| 用途 | 必要なもの |
|---|---|
| GitHub MCP | **Docker（起動済み）** + 環境変数 `GITHUB_PERSONAL_ACCESS_TOKEN` |
| Playwright MCP | Node.js / npx |
| Figma MCP | Figma Desktop アプリ（起動済み） |

#### Docker のインストール

```bash
# macOS
brew install --cask docker
open -a Docker  # Docker Desktop を起動

# Linux
# 公式ドキュメント参照: https://docs.docker.com/engine/install/
```

#### GitHub Personal Access Token の設定

シェル設定ファイル（`~/.zshrc` 等）に追記：

```bash
export GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxxxxxxxxxx
```

セキュリティ上の推奨：

- **Fine-grained PAT** を使い、必要なリポジトリ・スコープのみに限定する
- **有効期限を 30〜90 日** に設定して定期的にローテーションする
- 1Password CLI など秘密管理ツールを併用する場合は `export GITHUB_PERSONAL_ACCESS_TOKEN=$(op read "op://...")` のように動的に取得する

### インストール

```bash
git clone https://github.com/ShigetomoYamamoto/claude-config.git ~/dotfiles/claude-config
cd ~/dotfiles/claude-config
./setup.sh
```

`setup.sh` は以下を行います：
- `agents/`, `commands/`, `hooks/`, `rules/`, `skills/` を `~/.claude/` にコピー
- `settings.json.template` からパスを解決して `~/.claude/settings.json` を生成

## 自走開発の始め方

基盤が整った状態（`CLAUDE.md` + `docs/` に仕様・設計が記載済み）であれば、以下の3つの方法でいつでも自走開発を開始できます。

### 1. GitHub Issue を渡す

```
Issue #12 を実装して
```

Claude が Issue の内容を読み、仕様書・設計書・コードベースと照合した上で、計画 → 実装 → コミット → PR 作成まで自律的に進めます。

### 2. やりたいことを日本語で伝える

```
ユーザーのパスワードリセット機能を作って
```

```
ログイン時のエラーメッセージが表示されないバグを直して
```

Claude がタスクの内容を判断し、設計が必要なら `/design`、実装計画が必要なら `/plan` を自動的に起動して進めます。

### 3. コマンドで明示的に起動する

設計から始めたい場合：
```
/design パスワードリセット機能
```

実装計画から始めたい場合（設計済みの機能）：
```
/plan Issue #12 の実装
```

---

### Claude が自律的に行うこと

タスクを受け取った Claude は以下を順に実行します。ユーザーの承認が必要な場面では必ず提示して止まります。

```
1. 仕様・設計・コードベースの把握
2. 設計判断が必要 → /design（承認待ち）
3. 実装計画の立案 → /plan（承認待ち）
4. テストファーストで実装 → /tdd
5. コードレビュー → コミット（承認待ち）
6. コードレビュー → PR 作成（承認待ち）
```

---

## 使い方

### パターン1: 既存プロジェクトへの導入

仕様書・設計書など必要な資料が揃っている前提です。

**ステップ1: AI エージェント自走基盤を生成**
```
/init-autonomous
```

スタックを自動検出し、以下を一括生成します：
- `.claude/settings.json` — スタック固有コマンドの権限設定（npm/pest/pytest/go/cargo など）
- `CLAUDE.md` — プロジェクトルール・エンティティ・ロール定義
- `.claude/rules/`, `.claude/commands/`, `.claude/agents/` — スタック固有の設定
- `docs/` — 仕様書テンプレート・ADR・コードマップ
- `.github/` — CI/CD・PRテンプレート・Issue テンプレート

**ステップ2: 既存資料を Claude に読み込ませる**

`/init-autonomous` の実行中に「既存の仕様書・設計書はありますか？」と聞かれます。ファイルパスを答えると Claude が内容を読み取り、`CLAUDE.md` の参照パスを自動で更新します。

ここまで完了すると、Claude が仕様・設計・コードベースを把握した状態になります。以降は通常の開発フローで進めます。

```
# 通常の開発フロー
/plan      → /tdd      → /commit    → /create-pr
（実装計画）  （TDD実装）  （レビュー→コミット）  （レビュー→PR）
```

---

### パターン2: 新規プロジェクト作成直後

コードも資料もほぼない状態から始めます。まず要件定義・設計を行い、その成果物を使って自走基盤を構築します。

```
# ステップ1: 要件定義・システム設計
/design
```

機能要件・非機能要件・データモデル・APIコントラクトを定義します。承認するまで実装には進みません。

```
# ステップ2: AI エージェント自走基盤を生成
/init-autonomous
```

```
# ステップ3: 設計内容を docs/ に反映
docs/01_product-specifications.md  ← /design の要件定義を記入
docs/02_detailed-design.md         ← /design の詳細設計を記入
```

```
# ステップ4: 実装開始
/plan      → /tdd      → /commit    → /create-pr
```

---

## 別マシンで最新の設定を取得するとき

```bash
cd ~/dotfiles/claude-config
git pull
./setup.sh
```

## プラグイン（別マシンで手動インストールが必要）

設定ファイルに有効化フラグは含まれていますが、プラグイン本体は別途インストールが必要です：

```bash
claude plugin install slack
claude plugin install supabase
claude plugin install vercel
```
