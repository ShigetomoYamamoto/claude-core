# ADR-011: GitHub MCP は公式 `github` プラグイン（PAT ヘッダ）を利用する

**ステータス**: accepted

**日付**: 2026-06-19

## コンテキスト

[ADR-010](./010-official-remote-github-mcp.md) では「公式ホスト版リモート MCP（`https://api.githubcopilot.com/mcp/`）を OAuth で使えば Docker も PAT も不要になる」と判断し、`mcp.json` に URL のみを書いて Claude Code 内の `/mcp` から OAuth 認証する方式へ移行した。

しかし実際に接続すると、Claude Code が次のエラーで失敗した:

```
GitHub MCP Server
  Status: ✘ failed
  Issue:  Incompatible auth server: does not support dynamic client registration
  SDK auth failed: Incompatible auth server: does not support dynamic client registration
```

原因を OAuth フローを 1 段ずつ追って特定した:

1. `POST https://api.githubcopilot.com/mcp/`（無認証）→ `401` + ヘッダ
   `www-authenticate: Bearer ... resource_metadata="https://api.githubcopilot.com/.well-known/oauth-protected-resource/mcp/"`
2. その protected-resource メタデータが認可サーバーを指定:
   `"authorization_servers": ["https://github.com/login/oauth"]`
3. 認可サーバーのメタデータ（`https://github.com/.well-known/oauth-authorization-server/login/oauth`）には
   `authorization_endpoint` / `token_endpoint` はあるが **`registration_endpoint` が無い**。

Claude Code は GitHub 用の `client_id` を内蔵しないため、リモート MCP へは **動的クライアント登録（DCR / RFC 7591）** で自分をその場登録して OAuth する。GitHub の認可サーバーは DCR 非対応（`registration_endpoint` を公開せず、OAuth App / GitHub App の手動登録を要求する）ため、登録できず認証が始まる前に失敗する。

> VS Code / Copilot で同じ URL が OAuth で繋がるのは、それらが GitHub に事前登録済みの `client_id` を持つため。Claude Code は汎用サードパーティで `client_id` を持たず DCR に頼るしかないため、この URL では OAuth が成立しない。

つまり ADR-010 の前提（「Claude Code がこの DCR を回せる」）は成立しなかった。「OAuth だけで PAT 不要」は本構成では不可能である。

その後、GitHub が **公式 `github` プラグイン**（`claude-plugins-official` マーケットプレイス）を提供した。その `.mcp.json` は次の通りで、リモートサーバー + **PAT を `Authorization` ヘッダ（env 展開）で渡す**:

```json
{
  "github": {
    "type": "http",
    "url": "https://api.githubcopilot.com/mcp/",
    "headers": { "Authorization": "Bearer ${GITHUB_PERSONAL_ACCESS_TOKEN}" }
  }
}
```

これは「リモート（Docker 不要）+ PAT ヘッダ」方式そのもので、DCR の問題を回避しつつ Docker も避けられる。

## 検討した選択肢

1. **ADR-010 の OAuth 方式を継続** — DCR 非対応で接続不可。却下
2. **`mcp.json` に自前で PAT ヘッダ付き http サーバーを書く** — 動くが、認証方式・URL の保守を自前で抱える。公式プラグインと二重管理になる
3. **公式 `github` プラグインへ委譲**（`/plugin` で導入）— 認証方式・URL・更新を GitHub 公式が保守。`mcp.json` から GitHub を外せる
4. **Docker + PAT へ差し戻し**（[ADR-002](./002-docker-github-mcp.md)）— 動くが Docker 依存が復活

## 決定

**公式 `github` プラグインを利用する。** リポジトリの `mcp.json` からは GitHub エントリを削除し、各マシンで `/plugin` から公式プラグインを導入する。

プラグインは `Authorization: Bearer ${GITHUB_PERSONAL_ACCESS_TOKEN}` を使うため、**PAT が再び必要**になる。PAT は dotfiles に残さないため OS の Keychain / Keyring に保管し `~/.zprofile` で env 変数へ展開する（[ADR-005](./005-keychain-pat.md) を再有効化）。Docker は引き続き不要。

## 結果

### Positive

- Claude Code で実際に GitHub MCP が認証・接続できる（DCR 問題を回避）
- 認証方式・サーバー URL・サーバー更新を GitHub 公式が保守する。リポジトリは追従不要
- `mcp.json` から GitHub が消え、自前管理の対象が減る
- Docker は不要のまま（ADR-002 の差し戻しは回避）

### Negative

- **PAT が再び必要**になる（ADR-010 で狙った「PAT 完全廃止」は撤回）。発行・最小スコープ・ローテーション・Keychain 登録・env 展開（ADR-005）が復活する
- プラグイン導入が各マシンで 1 手間（`/plugin`）。`install.py` の対象外（プラグインは Claude Code 側が管理）
- 既存マシンでは `~/.claude.json` に残る旧 `GitHub`（http・認証ヘッダなし）が壊れたまま重複するため、`claude mcp remove GitHub` での除去が必要

## 関連

- 置き換え対象: [ADR-010](./010-official-remote-github-mcp.md)（公式リモート + OAuth。DCR 非対応で不成立）
- 再有効化: [ADR-005](./005-keychain-pat.md)（Keychain / Keyring での PAT 管理）
- 引き続き不採用: [ADR-002](./002-docker-github-mcp.md)（Docker 経由 GitHub MCP）
- 要件定義: `docs/requirements.md` セクション「セキュリティ」
- 自走時の push/PR 経路: `rules/loop-safety.md`（物理層スコープ。push/PR は `gh` CLI 経由のため GitHub MCP は対話用途）
