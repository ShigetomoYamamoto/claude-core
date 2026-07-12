# Migration Issue Mapping (ADR-023)

This maps the existing GitHub Issues in the pre-split repository to their
destination foundation under the 3-way split. **No remote Issue action
(transfer / create / close) is executed by this document or by ADR-023 itself.**
All rows are a plan only, pending human approval and the target repos existing.

| Issue# | 概要 | 移行先 repo | アクション | 根拠 |
|---|---|---|---|---|
| 71 | git-destructive-blocker: refspec/force push 保護ブランチ素通り | claude-engineering | 新repo作成後に移送 | git hook は engineering |
| 59 | git-destructive-blocker: git clean 正規表現 force push 誤爆 | claude-engineering | 新repo作成後に移送 | 同上 |
| 61 | collaboration-style に truth-first 追加 | claude-core | 現repo(=core)に残置 | collaboration-style は core |
| 52 | ECONNRESET: MCP/プラグイン重複整理 | claude-core(migration親) | 親Issueへ集約 | グローバルMCP/プラグイン整理は本移行の一部 |
| 46 | 調査を一級市民に | claude-core | 現repo(=core)に残置 | research は中立能力 |
| 45 | メタ学習(自己改善ループ) | claude-core | 現repo(=core)に残置 | memory/outer-loop は core |
| 44 | GitHub PR レビュー自動応答ループ | claude-engineering | 新repo作成後に移送 | PR/レビューは engineering |
| 43 | OpenAI codex cross-model レビュー | claude-engineering | 新repo作成後に移送 | レビューは engineering |
| 42 | 判断待ち構造化承認UI | claude-core | 現repo(=core)に残置 | ハーネスUXは中立 |
| 41 | 話題転換時の新セッション自動開始 | claude-core | 現repo(=core)に残置 | 中立ハーネス |
| 40 | コンテキスト自動 /compact | claude-core | 現repo(=core)に残置 | 中立ハーネス |
| 4 | 環境変数管理 | claude-engineering | 新repo作成後に移送 | 開発/プロジェクト |
| 3 | 依存関係更新 | claude-engineering | 新repo作成後に移送 | 開発 |
| 2 | リリースノート/CHANGELOG 生成 | claude-engineering | 新repo作成後に移送 | 開発 |

## 横断親 Issue（claude-core に新規作成予定）

- **title案**: 「Migrate: split config into core / engineering / work-agent foundations」
- **body 概要**: 本移行の親。engineering/work-agent の実装 Issue（新 repo 側）をリンクする集約 Issue。上表の「claude-core(migration親)」行（#52）はこの親 Issue に統合される。
- **リモート操作は未実行**（repo 作成後に人間承認の上で実施）。

## 注記

`gh issue transfer` は移送先 repo が存在することを要求するため、`claude-engineering`
行の移送はすべて engineering repo 作成後まで保留される。`claude-core` 行の Issue は
リネームされた repo（= 現 repo）にそのまま残るだけで、移送操作は不要。
