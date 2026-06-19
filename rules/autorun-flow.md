# Autorun Flow — 宣言的フロー定義（自走の遷移表）

`/autorun`（インタープリタ）が読む、フロー全体の「形」の単一の正。実行ロジックは持たず、
**どのフェーズを・どの順で・どこで止まるか**だけを宣言する。フェーズの中身は既存のコマンド /
エージェント / スキルが担う（部品の再利用）。安全規律の正本は `rules/loop-safety.md`。

## モード表（2モード = 起点とゴールのパラメータ違い）

| モード | 起点(start) | 最初のフェーズ | ゴール(goal) |
|--------|-------------|----------------|--------------|
| full-auto | 自由形式の目標 | requirements | deploy |
| support | 具体タスク / Issue | analyze-task | pr |

両モードは別物ではなく、同じ遷移表に与える起点・ゴールのパラメータ違い。

## フェーズ遷移表

| phase_id | 実行部品 | kind | success_test（機械的に判定） | full-auto next | support next |
|----------|----------|------|------------------------------|----------------|-------------|
| requirements | requirements-analyst | **gate** | 人間が要件を承認 | design | — |
| analyze-task | task-analyst | auto | 分解結果と受け入れ基準が出力された | plan | plan |
| design | architect | **gate**（スキップ可） | 人間が設計を承認 | plan | plan |
| plan | planner | auto | 計画にファイルパスと手順が揃う | tdd | tdd |
| tdd | `skills/loop-engineering/`（ミクロ層に委譲） | auto | テスト/lint/型チェック pass かつカバレッジ80%+（Bash 実測） | verify | verify |
| verify | `/review-loop`（委譲） | auto | reviewer が NO_ISSUES かつ機械チェック pass | commit | commit |
| commit | `/commit` | auto（※） | code-reviewer CRITICAL/HIGH=0 かつ secret-detection pass | pr | pr |
| pr | `/create-pr` | **gate** | 人間が PR を承認（push/PR は gh 経由） | migrate | （ゴール） |
| migrate | `/migrate` | auto（破壊的変更は確認） | マイグレーション成功 | deploy | — |
| deploy | `/deploy` | **gate** | 人間がデプロイを承認 | （ゴール） | — |

※ commit は kind=auto だが、`/autorun` 起動時に利用者から「自動コミット包括承認」を1回取得していることが前提（`rules/git-workflow.md` の自走時例外）。メッセージは毎回トランスクリプトに提示する。包括承認が無い場合は commit を gate 扱いにする。

## 関門（kind=gate、人間が必ず確認）

- **requirements** — 機械判定できない方向性（要件の妥当性）。手戻りが最大。
- **design** — 同上（アーキテクチャ判断）。ただし下記スキップ条件を満たせば gate ごとスキップ。
- **pr** — `git push` を伴う外向き不可逆。
- **deploy** — 本番反映の不可逆。

不可逆操作の停止点（pr / deploy / migrate の破壊的変更）の規範は `rules/loop-safety.md` が正本。

## design スキップ判定（入力は requirements フェーズの成果）

design に到達した時点では plan 未実行のため、**requirements の成果物**を入力に判定する。
requirements-analyst に「新規DBスキーマ / 新API / 技術選定 / システム境界の変更」の要否フラグを
出させ、すべて不要なら design gate をスキップして plan へ自動遷移する（誤って停止/スキップしない）。

## 機械検証可能性の前倒し（起動時）

`/autorun` 起動時に、通る全 auto フェーズの success_test がこのプロジェクトで機械検証可能か
（test / lint / typecheck コマンドの実在）を Bash で検出する。1つでも検出不能なら
「自走不可・不足を報告」して早期停止する（走り出してから腰砕けを防ぐ）。

## 止まってよい場所のホワイトリスト

自走が停止してよいのは以下のみ。これ以外で止まったら**定義違反**として検知・報告する:

1. 関門4点（requirements / design / pr / deploy）
2. ハードストップ到達（下記・二層）
3. フェーズ内リトライ上限
4. ゴール到達（full-auto=deploy / support=pr）
5. 起動時の Precondition 不足 / 機械検証不能による早期停止
6. 不可逆操作の確認（migrate の DROP/RENAME 等、`rules/loop-safety.md` が定義する不可逆操作全般）
7. 回復不能エラー（build-error-resolver の上限到達など）

## ハードストップ（二層）

- **フェーズ内予算**: verify=5ラウンド、tdd=ミクロ層（loop-engineering）の内部上限。各フェーズ既定。
- **全行程予算**: 総フェーズ遷移回数の上限 ＋ `rules/loop-safety.md` のセッション全体上限（既定 20ターン/30分）。フェーズ内予算と全行程予算は独立で、いずれか先に到達した方で停止する。

## 単発実行時（RUN_STATE 未宣言）

各コマンドを直接（`/requirements` 等）呼んだ場合は本フロー定義は適用されず、**各コマンド従来の
案内停止**に落ちる。自走（autorun 文脈で RUN_STATE が宣言されている）時のみ本定義の kind が効く。

## 関連

- `commands/autorun.md` — 本定義を解釈するインタープリタ
- `rules/loop-safety.md` — 安全規律の正本（ハードストップ・ゴールドリフト・不可逆操作）
- `docs/adr/007-autonomous-loop-execution.md` — 関門4点の決定
- `docs/adr/008-orchestration-declarative-flow.md` — 宣言的フロー方式と commit 包括承認の決定
- `skills/loop-engineering/SKILL.md` — tdd フェーズの実装部品（ミクロ層）
