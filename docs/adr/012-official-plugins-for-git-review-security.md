# ADR-012: git / レビュー / セキュリティを公式プラグインに寄せ、危険操作は hooks で制御する

**ステータス**: accepted

**日付**: 2026-06-19

## コンテキスト

自作の Skills / Commands / Agents が増え、保守負担とリストの煩雑さが問題になっていた。一方で公式マーケットプレイス `claude-plugins-official` に、本リポジトリの自作と重なる first-party プラグインが揃った:

- `commit-commands` — `/commit`（コミットのみ）・`/commit-push-pr`・`/clean_gone`
- `code-review` — `/code-review`（PR を多エージェントで信頼度スコア付きレビュー）
- `pr-review-toolkit` — `code-reviewer` ほか6専門エージェント（`silent-failure-hunter` / `pr-test-analyzer` / `type-design-analyzer` / `comment-analyzer` / `code-simplifier`）と `/review-pr`
- `security-guidance` — hook 群（編集時のパターン警告・Stop/commit 時の LLM diff レビュー）

調査の結果、**危険な操作は既存 hooks がほぼ完全に担保している**ことが分かった:

| 危険操作 | 担保する hook |
|---|---|
| 保護ブランチへの commit / push、保護ブランチへの force push | `git-destructive-blocker.py` |
| PR ベースが develop 以外、または `--base` 未指定 | `pr-base-checker.py`（両方 exit 2 でブロック） |
| シークレットのステージ / ハードコード検出 | `git-add-secret-blocker.py` / `secret-detection.py` |
| 保護ブランチ上でのファイル編集 | `protected-branch-edit-guard.py` |

つまり「コマンドを公式の薄いものに替えても、危険な部分は hooks が止める」。残る差分は安全ではなく**規約・スタイル**（コミットメッセージ規約など）だけだった。

## 検討した選択肢

1. **全面自作維持** — 保守負担と煩雑さが解消しない。却下
2. **全面公式化** — 公式 commit-commands は薄く、`/commit-push-pr` は無確認 push/PR で `rules/git-workflow.md`・`rules/loop-safety.md` に反する。安全規約を失う。却下
3. **折衷（採用）** — 「**危険操作は hooks で決定的に制御し、振る舞い（コマンド・エージェント）は公式に寄せる**」。公式に良い同等品があるものだけ委譲し、無いものは自作維持する。規約の parity は小さな hook で補う。

## 決定

「危険操作 = hooks／振る舞い = 公式」を方針とする。

### 公式へ委譲（自作を削除）

| 削除した自作 | 委譲先 |
|---|---|
| `commands/commit.md` | `/commit-commands:commit`（コミットのみ・push しない） |
| `commands/delete-merged-branches.md` | `/commit-commands:clean_gone` |
| `commands/code-review.md`＋`agents/code-reviewer.md` | `pr-review-toolkit` の `code-reviewer`（opus・CLAUDE.md 準拠・多観点） |
| `skills/security-review/` | `security-guidance`（受動レビュー）＋ `rules/security.md`（規約） |
| `skills/tdd-workflow/` | 重複削除（`rules/testing.md`＋`/tdd`＋`tdd-guide` と内容重複） |

### 自作を維持（公式に良い同等品が無い／hook と衝突する）

| 維持する自作 | 理由 |
|---|---|
| `agents/security-reviewer.md` | `security-guidance` は hook のみで、ループから呼べる agent を持たない |
| `agents/reviewer.md`・`agents/fixer.md` | `/review-loop` 系・`loop-engineering`・workflow のエンジン。`fixer` に公式同等品なし |
| `commands/create-pr.md` | 公式 `/commit-push-pr` は `--base` 未指定で `pr-base-checker`（develop 強制）に弾かれ、かつ無確認 push/PR になる |
| `commands/create-branch.md` | develop 起点＋命名規約。公式に同等品なし |

### 安全は hooks に集約

既存 hook（`git-destructive-blocker` / `pr-base-checker` / `git-add-secret-blocker` / `secret-detection` / `protected-branch-edit-guard`）に加え、規約 parity のため **`commit-msg-convention.py`** を新設（Conventional Commits 形式を機械チェック。コマンド置換・heredoc・読めない場合は fail open）。

プラグインの有効化は `settings.json.template` の `enabledPlugins`（`commit-commands` / `pr-review-toolkit` / `security-guidance`）。各マシンでは `/plugin` で導入する（`install.py` の対象外）。

## 結果

### Positive

- 自作コマンド/エージェント/スキルが減り、保守は公式が担う
- コードレビューが opus・多エージェント（pr-review-toolkit）へ強化される
- セキュリティが編集時警告＋commit 時 LLM レビュー（security-guidance）で常時働く
- 「危険操作は hooks」が明文化され、どのコマンド経由でも安全保証が一貫する

### Negative

- 公式プラグインを各マシンで `/plugin` 導入する手間が増える（`install.py` 対象外）
- コミット前の code-reviewer ゲート（旧 `/commit` 内）は弱まる。`security-guidance` の commit 時レビュー＋コード変更時の `code-reviewer` トリガー（`rules/agents.md`）で代替
- 公式 `/commit` はメッセージ規約を強制しない。規約は `commit-msg-convention.py` hook で担保する
- 公式 `pr-review-toolkit` の `code-reviewer` は CLAUDE.md を読むが、グローバル `rules/` を直接は読まない（コンテキスト注入で補う）

## 関連

- [ADR-001](./001-two-layer-architecture.md) — 二層アーキテクチャ（グローバル設定とプロジェクト設定の分離）
- [ADR-011](./011-official-github-plugin.md) — 公式 `github` プラグイン採用（同じ「公式委譲」方針の GitHub MCP 版）
- `rules/agents.md` — Proactive Agent Invocation 表と公式委譲の注記
- `rules/git-workflow.md` — コマンドの所在（公式委譲）
- `hooks/commit-msg-convention.py` — 規約 parity の新 hook
