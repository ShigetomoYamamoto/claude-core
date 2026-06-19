---
name: 自走モード
description: |
  目的を渡すと autorun-flow.md の定義に従い、完了条件まで関門4点以外を自動連結して自走します。
  関門(要件確定/設計確定/PR作成/デプロイ)と不可逆操作でのみ人間が確認します。
---

# /autorun — 自走モード（関門付きフロー自走インタープリタ）

目的を1つ渡すと、`rules/autorun-flow.md`（フロー定義）を解釈し、完了条件まで人間のコマンド
打鍵なしでフェーズを自動連結する。関門4点と不可逆操作でのみ停止する。安全規律の正本は
`rules/loop-safety.md`。

## ステップ 1: 起動時チェック

1. **Preconditions** — `rules/loop-safety.md` の前提条件を満たすか確認。
2. **機械検証可能性の前倒し** — 通る全 auto フェーズ（autorun-flow.md）の success_test が
   このプロジェクトで機械検証可能か（test / lint / typecheck コマンドの実在）を Bash で検出。
   1つでも不能なら「自走不可・不足を報告」して停止。
3. **専用ブランチ確認** — `main`/`master`/`develop` なら先に `/create-branch`（`rules/agents.md`
   の Pre-Implementation Branch Check）。develop 不在なら現作業ブランチ、protected なら新規分岐。
4. **ハードストップ設定** — 未指定なら全行程の既定（遷移回数上限 ＋ 20ターン/30分）を提示し合意。
5. **commit 包括承認** — 「自走中、関門以外の commit を確認なしで自動実行してよいか」を1回だけ
   確認し承認を得る（`rules/git-workflow.md` の自走時例外）。承認が得られなければ commit を
   gate 扱いにする。

## ステップ 2: モード判定

入力が自由形式の目標 → full-auto / 具体タスク・Issue → support。autorun-flow.md のモード表から
start / goal を取得する。

## ステップ 3: RUN_STATE 初期化（会話内に可視化）

`RUN_STATE = { mode, current_phase, goal_phase, phase_outputs, gates_passed, budget, branch, commit_blanket_approved }`
を初期化し transcript に表示する（loop-safety の「全ステップを出す」準拠）。肥大化したら直近 1-2
フェーズ重視で要約圧縮する（`commands/review-loop.md` の引き継ぎ規律に倣う）。

## ステップ 4: 反復ループ

current_phase が goal_phase を越えるまで繰り返す:

1. `rules/autorun-flow.md` を読み、current_phase の行を引く。
2. 実行部品を起動する（GOAL 再掲・直前フェーズ成果・SCOPE をプリアンブルで明示的に渡す）。
   - **tdd** フェーズは `skills/loop-engineering/`（ミクロ層）に委譲。
   - **verify** フェーズは `/review-loop` に委譲。
3. success_test を**機械的に実行**（Bash、結果を transcript 出力。自己申告で代替しない）。
4. 偽なら: フェーズ内リトライ（tdd/verify は内部ループ、build エラーは build-error-resolver）。
   フェーズ内上限 or 膠着で STOP・報告。
5. 真なら kind 分岐:
   - **auto** — 確認を取らず next へ自動遷移。commit フェーズは包括承認のもと自動（メッセージは提示）。
   - **gate** — 停止プロトコル（関門名・成果サマリ・次に進むと何が起きるか・承認/修正/中止を提示し
     **能動的にターン終了**）。承認後のみ next。承認は gates_passed に記録し次に持ち越さない。
6. **design スキップ** — autorun-flow.md のスキップ条件（requirements 成果で判定）を満たせば
   design gate ごとスキップして plan へ。
7. **ゴールドリフト検知** — 各フェーズ境界で (a) 構造ゴール=goal_phase 到達、(b) 内容ゴール=確定要件
   への各成果の写像、の両方を確認。内容がズレたら新目標を作らず STOP・報告。

## ステップ 5: 停止と報告

ゴール到達 / 関門待ち / ハードストップ / 異常停止のいずれかで停止し、停止区分を明示する。
**止まってよい場所のホワイトリスト**（autorun-flow.md）以外で止まったら定義違反として検知・報告。
`rules/memory.md` に従い「次回が知るべき学習」を `memory/` に書き戻してから報告する。

## 不可逆操作（loop-safety 準拠）

- push / deploy / delete / 外部送信は自走中でも人間確認（関門 pr / deploy がこれを担う）。
- push / PR は **gh CLI（Bash）経由**で行い、物理層の `pr-base-checker.py` /
  `git-destructive-blocker.py` が効くようにする（MCP 経由は物理層が抜けるため避ける）。

## 関連

- `rules/autorun-flow.md` — フロー定義（本コマンドが解釈する正）
- `rules/loop-safety.md` — 安全規律の正本
- `skills/loop-engineering/SKILL.md` — tdd フェーズの実装部品（ミクロ層）
- `docs/adr/007-autonomous-loop-execution.md` / `docs/adr/008-orchestration-declarative-flow.md` — 設計決定
