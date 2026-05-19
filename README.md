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
| `commands/` | スラッシュコマンド（/init-autonomous, /plan, /tdd, /commit, /create-pr など） |
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

```bash
git clone https://github.com/ShigetomoYamamoto/claude-config.git ~/dotfiles/claude-config
cd ~/dotfiles/claude-config
./setup.sh
```

`setup.sh` は以下を行います：
- `agents/`, `commands/`, `hooks/`, `rules/`, `skills/` を `~/.claude/` にコピー
- `settings.json.template` からパスを解決して `~/.claude/settings.json` を生成

## 新しいプロジェクトで自走基盤を整える

グローバル設定インストール後、プロジェクトディレクトリで以下を実行します：

```
/init-autonomous
```

スタックを自動検出し、以下を一括生成します：
- `.claude/settings.json` — スタック固有コマンドの権限設定（npm/pest/pytest/go/cargo など）
- `CLAUDE.md` — プロジェクトルール・エンティティ・ロール定義
- `.claude/rules/`, `.claude/commands/`, `.claude/agents/` — スタック固有の設定
- `docs/` — 仕様書テンプレート・ADR・コードマップ
- `.github/` — CI/CD・PRテンプレート・Issue テンプレート

生成後は `docs/01_product-specifications.md` と `docs/02_detailed-design.md` を記入することで、エージェントが Issue 番号から PR 作成まで全自動で動く状態になります。

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
