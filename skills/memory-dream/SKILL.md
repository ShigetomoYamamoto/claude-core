---
name: memory-dream
description: 蓄積したナレッジベース全体——公式 auto-memory（~/.claude/projects/*/memory/）に加え、自作の Skills・スラッシュコマンド（プロンプト群）・rules・ADR・workflows——を Fable に丸ごと読み込ませ、重複・矛盾・陳腐化を洗い出して整理する consolidation 手順。今後の作業精度を上げるための定期棚卸しに使う。
---

# memory dream（ナレッジベースの整理／consolidation）

セッションを跨いで溜まった**ナレッジベース全体**を Fable に丸ごと読ませ、重複・矛盾・陳腐化を排除して「いま正しく動く知見」だけに整える手順。対象は2層に分かれ、**層ごとに反映方法（＝安全策）が違う**のが肝。

## 対象の2層と反映方針（最重要）

| 層 | 実体 | 反映方法 |
|---|---|---|
| **A. auto-memory** | `~/.claude/projects/*/memory/*.md` と `MEMORY.md` 索引 | consolidation 対象。編集・削除・剪定を**直接**行う（`rules/memory.md` 準拠）。 |
| **B. バージョン管理された知見** | 自作 `skills/*/SKILL.md`、`commands/*.md`（スラッシュコマンド＝プロンプト群）、`rules/*.md`、`docs/adr/*.md`、`workflows/*` | **全読して分析対象にする**が、変更は**提案として出し、通常の git フロー（develop 起点ブランチ→PR→hooks→人間承認）で反映**する。auto 破壊書き換えはしない。 |

**なぜ層で分けるか**: A は auto-memory でありエージェントが書き換える前提の領域。B はバージョン管理された手書き資産（特に ADR は「その時点の意思決定の記録」）で、黙って書き換えると意思決定の履歴やレビュー機構（hooks）を壊す。だから B は「読んで矛盾・重複・陳腐化を**指摘**し、直しは通常の変更手続きに乗せる」。ADR は原則**書き換えず**、古い決定は新しい ADR で supersede する（既存 ADR 本文の改変は提案しない）。

## 実行モデル（推論=Fable / 実行=委譲）

- **推論・分析**（丸ごと読み込んで重複・矛盾・陳腐化を見抜く）は **Fable**（最上位の推論モデル）が担う。コンテキストが大きいので、可能なら専用セッションで層・カテゴリ単位に読み込む。
- **実行**（記憶ファイルの編集・削除、提案のブランチ化・コミット）は **Sonnet 実行エージェントへ委譲**（`executor` / `git-runner`）。main-loop の推論モデルは `opus-execution-guard` で Edit/Write/state-changing Bash がブロックされるため委譲が必須。`rules/role-separation.md` 準拠。

## 1. 収集（Mine）— ナレッジベースを丸ごと集める

Fable に全体を渡すため、両層をリストアップして読み込む。

```bash
# --- A. auto-memory（全プロジェクト・~/.claude 配下すべて） ---
find ~/.claude/projects -type f -path '*/memory/*.md'
# プロジェクト別の記憶数（肥大したものから着手）
for d in ~/.claude/projects/*/memory; do
  echo "$(find "$d" -maxdepth 1 -name '*.md' ! -name MEMORY.md | wc -l | tr -d ' ')  $(basename "$(dirname "$d")")"
done | sort -rn

# --- B. バージョン管理された知見（dotfiles リポジトリ内） ---
find skills -name 'SKILL.md'
find commands -name '*.md'
find rules -name '*.md'
find docs/adr -name '*.md' 2>/dev/null
find workflows -type f 2>/dev/null
```

大きすぎて1コンテキストに載らない場合は層・カテゴリ単位で分割して読み込み、分析結果（重複・矛盾・陳腐化の一覧）を先に作ってから反映に移る。

## 2. 分析（Analyze）— Fable が全体を突き合わせる

丸ごと読んだうえで、**層をまたいで**次を洗い出す:

- **重複**: 同じルール/手順が複数の skill・command・rule・memory に再掲されていないか。上位（`rules/*.md`）が定める世界のルールは下位で再掲しない（`rules/memory.md`）。
- **矛盾**: skill と rule、memory と現行コード、古い ADR と新しい運用が食い違っていないか。
- **陳腐化**: 存在しないファイル・削除済み関数・廃止フラグ・撤回された手順への参照。現存確認して残っていなければ除去/更新。
- **相対日付**: 「昨日」「先週」等は実行時点基準の**絶対日付**（例: 2026年7月4日）へ変換。

## 3. 反映（Apply）— 層ごとに方法を変える

- **A. auto-memory**: 重複統合・矛盾解消・陳腐化除去を直接行う。フォーマットは公式に従い**1ファイル1事実**を保つ。`feedback`/`project` 型の **Why:** は動機としての技術的因果なので残す。
- **B. バージョン管理された知見**: 変更は**提案**にまとめ、`rules/git-workflow.md` に従い develop 起点ブランチ→PR で反映（hooks と人間レビューを通す）。**ADR 本文は書き換えず**、古い決定は supersede する新 ADR を提案。skill/command/rule の重複は、上位に一本化して下位から削る形で提案。

## 4. 剪定と索引の同期（Prune & Index）

記憶本文と `MEMORY.md` 索引に「メタな経緯・履歴」を残さない。

- **除外**: 重複回避の言い訳注記／経緯・失敗談（技術的因果以外）／学習日・セッションID・指摘者などのメタデータ。
- **残す**: いま正しく動く手順・知見・技術的因果（AだとBが壊れるためC）。`feedback`/`project` 型の **Why:** は保持。
- **索引同期**: `MEMORY.md` は「1記憶=1行（`- [Title](file.md) — hook`）」。**find で丸ごと再生成しない**（title/hook が消える）。実ファイルと索引の差分を検出して手当て:

```bash
cd ~/.claude/projects/<project-slug>/memory
comm -3 \
  <(ls *.md | grep -vx MEMORY.md | sort) \
  <(grep -oE '\(([A-Za-z0-9._-]+\.md)\)' MEMORY.md | tr -d '()' | sort)
# 左のみ=索引漏れ / 右のみ=実体なし参照
```

## 5. チェックリスト（完了前の確認）

- [ ] A（`~/.claude/projects/*/memory/` 全体・ホーム/グローバル寄り含む）と B（skills/commands/rules/ADR/workflows）の両方を Fable に読み込ませた
- [ ] 相対日付をすべて絶対日付へ変換した
- [ ] 層をまたぐ重複・矛盾・陳腐化を洗い出した（上位ルールの下位再掲を排除）
- [ ] A は直接整理し、B は提案として git フロー（develop 起点→PR）に乗せた（黙って書き換えていない）
- [ ] ADR 本文は改変せず、必要なら supersede 新 ADR を提案した
- [ ] 記憶本文・`MEMORY.md` から経緯・履歴を除いた（`feedback`/`project` 型の **Why:** は保持）
- [ ] 存在しないファイル/シンボル/フラグ参照を除去 or 現存確認した
- [ ] `MEMORY.md` 索引と `memory/*.md` の実体が一致
- [ ] 編集・削除・コミットは Sonnet 実行エージェント（`executor`/`git-runner`）へ委譲した
- [ ] 成果は push せず、ユーザーがレビューできる状態にした
