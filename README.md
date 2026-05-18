# claude-config

Claude Code のグローバル設定を管理する dotfiles リポジトリ。

## 含まれるもの

| ディレクトリ/ファイル | 内容 |
|---|---|
| `agents/` | カスタムエージェント定義（planner, tdd-guide, code-reviewer など） |
| `commands/` | スラッシュコマンド（/plan, /tdd, /code-review など） |
| `hooks/` | フックスクリプト（console.log 警告、シークレット検出など） |
| `rules/` | コーディングスタイル、テスト要件、セキュリティガイドライン |
| `skills/` | 参照ドキュメント（フロントエンド/バックエンドパターンなど） |
| `settings.json.template` | Claude Code 設定テンプレート（パスはインストール時に自動解決） |

## 新しいマシンへのインストール

```bash
git clone https://github.com/ShigetomoYamamoto/claude-config.git ~/dotfiles/claude-config
cd ~/dotfiles/claude-config
./setup.sh
```

`setup.sh` は以下を行います：
- `agents/`, `commands/`, `hooks/`, `rules/`, `skills/` を `~/.claude/` にコピー
- `settings.json.template` からパスを解決して `~/.claude/settings.json` を生成

## このマシンで設定を変更したとき

`~/.claude/` 内のファイルを編集した後、以下を実行してリポジトリに反映します：

```bash
cd ~/dotfiles/claude-config
./sync.sh
git add .
git commit -m "..."
git push
```

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
