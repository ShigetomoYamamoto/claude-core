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

## ステップ 3: リモートへのプッシュ（未プッシュの場合）

現在のブランチがリモートに存在しない、または未プッシュのコミットがある場合：

```bash
git push -u origin <current-branch>
```

## ステップ 4: PRタイトルとDescription の生成

### タイトルのルール

- 70文字以内
- `type: 内容` 形式（Conventional Commits に準拠）
- 日本語で記述

### Description テンプレート

```markdown
## Summary
- <変更点1>
- <変更点2>
- <変更点3（必要に応じて）>

## Test plan
- [ ] <確認項目1>
- [ ] <確認項目2>
- [ ] <確認項目3（必要に応じて）>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

### Summary の書き方

- コミット履歴と差分から変更内容を箇条書きで3点程度にまとめる
- 「何を」「なぜ」変えたかを端的に記述する
- 技術的な詳細よりもレビュアーが理解しやすい説明を優先する

### Test plan の書き方

- 変更した機能・修正したバグに対して手動確認すべき項目を列挙する
- ゲーム・UI変更の場合は具体的な操作手順を記載する
- 「〜が正しく動作することを確認」という形式で記述する

## ステップ 5: PR作成前の確認

生成したタイトルと Description をユーザーに提示して承認を得る。

## ステップ 6: PR作成実行

```bash
gh pr create \
  --base develop \
  --title "<生成したタイトル>" \
  --body "$(cat <<'EOF'
<生成した Description>
EOF
)"
```

## ステップ 7: 完了報告

PR作成後、以下を表示する：

- PR の URL
- タイトル
- base ブランチ → head ブランチ

## 注意事項

⚠️ **PRを作成する前に必ずタイトルと Description をユーザーに確認すること。**

⚠️ **base ブランチは常に `develop` とする。**（main / master へのダイレクトPRは行わない）

⚠️ **未コミットの変更がある場合は `/commit` スキルを先に実行するよう案内すること。**
