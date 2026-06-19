# ADR-010: GitHub MCP は公式ホスト版リモートサーバー（OAuth）を利用する

**ステータス**: accepted

**日付**: 2026-06-19

## コンテキスト

当初は GitHub MCP を Docker コンテナ（`ghcr.io/github/github-mcp-server`）で起動し、Personal Access Token（PAT）を環境変数経由で渡していた（[ADR-002](./002-docker-github-mcp.md)）。PAT は dotfiles への混入を避けるため OS の Keychain / Keyring に保管していた（[ADR-005](./005-keychain-pat.md)）。

この構成は次のコストを抱えていた:

- **Docker 必須** — Docker Desktop / Engine のインストールと起動が前提。Windows は WSL2 必須で実質非対応。
- **PAT 管理の手間** — 発行・最小スコープ設定・30〜90 日のローテーション・Keychain 登録・`~/.zprofile` での環境変数展開。OS ごとに手順が分岐（macOS は `security`、Linux は `secret-tool`）。
- **コンテナ起動オーバーヘッド**が毎回発生。

その後、GitHub が**公式ホスト版リモート MCP サーバー**（`https://api.githubcopilot.com/mcp/`、OAuth 認証）を提供し、Claude Code もリモート MCP の OAuth 認証に対応した。Docker も PAT も不要になる。

## 検討した選択肢

1. **Docker + PAT 方式を継続**（ADR-002/005）— 自前インフラを保守し続ける。Docker 依存・PAT 運用の手間が残る
2. **公式リモートサーバー（OAuth）へ移行** — `mcp.json` に URL のみ記載し、Claude Code 内で OAuth 認証。Docker・PAT 不要
3. **ローカル `github-mcp-server` バイナリを直接起動** — Docker は外せるが PAT 管理は残る

## 決定

**公式ホスト版リモート GitHub MCP サーバー（OAuth）へ移行する。**

`mcp.json`:

```json
"GitHub": {
  "type": "http",
  "url": "https://api.githubcopilot.com/mcp/"
}
```

`mcp.json` には URL のみを記載し、トークンは一切含めない。認証は `setup.sh` 適用後に Claude Code 内で `/mcp` から OAuth で行う。OAuth トークンは Claude Code が保管する。

## 結果

### Positive

- **Docker が不要**になり、前提ツール・preflight チェックから除外。Windows 非対応の主因も解消
- **PAT が不要**になり、発行・スコープ管理・ローテーション・Keychain 登録・環境変数展開がすべて消える（ADR-002/005 が役目を終える）
- `mcp.json` にも環境変数にもシークレットが一切残らない
- サーバーは GitHub が公式に運用・更新する

### Negative

- **OAuth は対話的なブラウザ認証が必要** — 完全ヘッドレス / cron 実行では認証が乗らない場合がある。ただし本リポジトリの自走フローは push/PR を `gh` CLI（Bash）経由で行う設計（`rules/loop-safety.md`）のため、GitHub MCP は対話用途に限られ実害は小さい
- **ネットワーク接続が前提**（ローカル Docker 実行ではなくなる）
- 既存マシンでは旧 `GitHub`（docker）エントリが `~/.claude.json` に残るため、`claude mcp remove GitHub` → `./setup.sh` 再実行での切り替えが必要（`install.py` の MCP マージは不足分のみ追加するため自動置換しない）

## 関連

- 置き換え対象: [ADR-002](./002-docker-github-mcp.md)（Docker 経由 GitHub MCP）, [ADR-005](./005-keychain-pat.md)（Keychain での PAT 管理）
- 要件定義: `docs/requirements.md` セクション「セキュリティ」「制約・前提条件」
- 自走時の push/PR 経路: `rules/loop-safety.md`（物理層スコープ）
