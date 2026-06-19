---
name: PR作成
description: |
  現在のブランチと develop の差分を分析し、
  テンプレートに沿った Pull Request を gh コマンドで作成します。
args:
  - name: タイトルヒント
    description: |
      PRタイトルのヒントになる情報（任意）。
      省略した場合はコミット履歴から自動生成します。
      例: 「倉庫番ゲームの重なりバグ修正」
    required: false
---

# PR作成手順

## ステップ 1: 現状確認

以下を並行して実行する：

- `git status` — 未コミットの変更がないか確認
- `git log develop...HEAD --oneline` — このブランチのコミット一覧
- `git diff develop...HEAD --stat` — 変更ファイルの統計

⚠️ **未コミットの変更がある場合は警告して停止する。** コミットを先に完了させること。

## ステップ 2: 差分の詳細分析

```bash
git diff develop...HEAD
```

全差分を読み込み、以下を把握する：

- 変更の目的（バグ修正 / 機能追加 / リファクタリング など）
- 影響範囲（どのシステム・機能に関わるか）
- 注目すべき実装の変更点

## ステップ 3: コードレビュー

**code-reviewer エージェント**を起動して `git diff develop...HEAD` の全差分をレビューする。

- CRITICAL / HIGH の指摘があれば **PR作成を中断し、先に修正してコミットする**
- MEDIUM 以下の指摘はユーザーに提示した上で続行してよい

差分に以下のいずれかが含まれる場合は **security-reviewer エージェント**も追加で起動する：
- 認証・セッション・トークン処理
- ユーザー入力のバリデーション・サニタイズ
- API エンドポイントの追加・変更
- シークレット・環境変数の参照
- 決済・課金・個人情報の処理

## ステップ 5: リモートへのプッシュ（未プッシュの場合）

現在のブランチがリモートに存在しない、または未プッシュのコミットがある場合：

```bash
git push -u origin <current-branch>
```

## ステップ 6: PRタイトルとDescription の生成

Description テンプレート・Summary/Test plan の書き方は `~/.claude/skills/git-workflow/SKILL.md` を参照すること。

### タイトルのルール

- 70文字以内
- `type: 内容` 形式（Conventional Commits に準拠）
- 日本語で記述

## ステップ 7: PR作成前の確認

生成したタイトルと Description をユーザーに提示して承認を得る。

## ステップ 8: PR作成実行

```bash
gh pr create \
  --base develop \
  --title "<生成したタイトル>" \
  --body "$(cat <<'EOF'
<生成した Description>
EOF
)"
```

## ステップ 9: 完了報告

PR作成後、以下を表示する：

- PR の URL
- タイトル
- base ブランチ → head ブランチ

## 注意事項

⚠️ **PRを作成する前に必ずタイトルと Description をユーザーに確認すること。**

⚠️ **base ブランチは常に `develop` とする。**（main / master へのダイレクトPRは行わない）

⚠️ **未コミットの変更がある場合は `/commit-commands:commit` を先に実行するよう案内すること。**
