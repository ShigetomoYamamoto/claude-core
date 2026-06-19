# ADR-005: GitHub PAT は OS 標準の Keychain / Keyring で管理する

**ステータス**: accepted（[ADR-011](./011-official-github-plugin.md) により再有効化。2026-06-19）

**日付**: 2026-05-21

> **経緯（2026-06-19）**: 一時 [ADR-010](./010-official-remote-github-mcp.md)（公式リモート + OAuth）で PAT 自体が不要になるとして superseded にしたが、その OAuth は DCR 非対応で成立しなかった。代わりに採用した公式 `github` プラグイン（[ADR-011](./011-official-github-plugin.md)）が `Authorization: Bearer ${GITHUB_PERSONAL_ACCESS_TOKEN}` を使うため PAT が再び必要になり、本 ADR（Keychain / Keyring での PAT 管理）を再有効化した。

## コンテキスト

GitHub PAT を環境変数経由で MCP に渡す必要がある（ADR-002）。環境変数の値をどこから取得するかは別問題。シェル設定ファイルに直書きするか、秘密管理ツールから取得するかの判断が必要。

## 検討した選択肢

1. **シェル設定ファイルに直書き** — `~/.zshrc` に `export GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...` と書く。dotfiles に混入する危険性
2. **1Password CLI** — クロスプラットフォーム。但し外部ツール依存
3. **macOS Keychain（`security` コマンド）** — OS 標準。macOS 専用
4. **Linux Keyring（`secret-tool` / libsecret）** — Linux GUI 環境で標準
5. **OS 別に Keychain / Keyring を併用** — macOS と Linux で別ツールを使う

## 決定

**OS 別に Keychain / Keyring を併用する。**

### macOS 手順

```bash
security add-generic-password -a "$USER" -s "github-pat" -w "ghp_xxxx"
# ~/.zprofile に追記
export GITHUB_PERSONAL_ACCESS_TOKEN="$(security find-generic-password -a "$USER" -s "github-pat" -w)"
```

### Linux 手順（GUI 環境前提）

```bash
sudo apt install libsecret-tools  # または sudo dnf install libsecret
secret-tool store --label="github-pat" service github-pat
# ~/.zprofile に追記
export GITHUB_PERSONAL_ACCESS_TOKEN="$(secret-tool lookup service github-pat)"
```

### 運用ルール

- Fine-grained PAT を使用
- 有効期限 30〜90 日で定期ローテーション
- スコープは最小限（必要なリポジトリ・権限のみ）
- `.git/config` への直書き厳禁

## 結果

### Positive

- PAT が暗号化された OS 標準ストアに保管される
- シェル設定ファイル（dotfiles）にトークンが残らない
- 外部ツール依存なし（OS 標準機能）
- 複数マシンで同じ手順を踏めば再現できる

### Negative

- macOS と Linux で別コマンドを使う必要がある
- Linux はヘッドレス環境では使えない（GUI 環境前提）
- PAT 更新時の手順（Keychain 上書き・gh CLI 再ログイン）が必要

## 関連

- 要件定義: `docs/requirements.md` セクション「セキュリティ」
- 再有効化の経緯: [ADR-011](./011-official-github-plugin.md)（公式 `github` プラグイン採用で PAT が再び必要に）
- 関連 ADR: [ADR-002](./002-docker-github-mcp.md)（Docker 経由 GitHub MCP・現在は不採用）
