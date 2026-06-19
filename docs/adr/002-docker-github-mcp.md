# ADR-002: GitHub MCP は Docker 経由で起動する

**ステータス**: superseded（[ADR-010](./010-official-remote-github-mcp.md) により置き換え。2026-06-19）

**日付**: 2026-05-21

> **注記（2026-06-19）**: GitHub が公式ホスト版リモート MCP サーバー（OAuth）を提供したため、Docker + PAT 方式は ADR-010 に置き換えられた。以下は当時の判断の記録。

## コンテキスト

GitHub MCP サーバーには Personal Access Token を渡す必要がある。設定ファイル（`~/.claude.json` や `mcp.json`）に直接書くと、dotfiles リポジトリにシークレットが混入する。

## 検討した選択肢

1. **PAT を `mcp.json` に直書き** — シンプル。dotfiles をパブリックリポジトリにできない。重大なセキュリティリスク
2. **`.mcp.local.json` でオーバーライド** — Claude Code が読み分けてくれる前提が必要。仕組みが複雑
3. **npx ベース MCP + 環境変数** — Docker 不要だが、Node プロセスへの env 渡しがプラットフォーム依存
4. **Docker コンテナ + 環境変数** — `command: docker` と `-e GITHUB_PERSONAL_ACCESS_TOKEN`（変数名のみ）を記載。実値は shell 環境変数から供給

## 決定

**Docker コンテナで GitHub MCP を起動し、PAT は環境変数経由でコンテナに渡す。**

`mcp.json` の例:

```json
"GitHub": {
  "type": "stdio",
  "command": "docker",
  "args": ["run", "-i", "--rm", "-e", "GITHUB_PERSONAL_ACCESS_TOKEN", "ghcr.io/github/github-mcp-server"]
}
```

## 結果

### Positive

- リポジトリにシークレットが一切含まれない
- ローテーション時はシェル環境変数を書き換えるだけ
- Keychain / 1Password CLI など秘密管理ツールとの統合が容易
- MCP サーバーのバージョン管理が Docker イメージタグで完結

### Negative

- **Docker が必須前提**になる（macOS/Linux で Docker Desktop / Engine が必要）
- Docker 未起動だと GitHub MCP が動かない
- コンテナ起動オーバーヘッドが毎回発生
- Windows での動作は WSL2 必須となり、サポート対象から外れる

## 関連

- 要件定義: `docs/requirements.md` セクション「セキュリティ」
- 関連 ADR: ADR-005（Keychain/libsecret での PAT 管理）
