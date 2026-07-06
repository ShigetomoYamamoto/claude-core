# ADR-008: オーケストレーション層に宣言的フロー定義方式を採用する

**ステータス**: accepted

**日付**: 2026-06-19

> **注記（2026-07-06）**: フロー定義ファイルの置き場所は [ADR-022](./022-autorun-flow-out-of-always-loaded-rules.md) により `rules/autorun-flow.md` から `docs/autorun-flow.md` へ移動した（rules/ 全域が毎セッション常時ロードされる文脈コストの解消）。「宣言的フロー定義が単一の正・3層分離」という本決定自体は不変。

## コンテキスト

ADR-007 で「関門付きループ自走」の挙動（関門4点・自動連結・2モード統合）を定義したが、
「オーケストレーション層の実装は別 ADR / PR で扱う」と委譲した。本 ADR はその実装方式を決める。

このリポジトリは markdown を Claude が読んで実行する仕組みで、実行ランタイムは無い。
"オーケストレーション" も「Claude が手順書を読み、同一会話で実行を継続する」ことで実現する。

## 検討した選択肢

1. **単一オーケストレーターコマンド方式（A）** — autorun.md に FSM 遷移表・関門表・各フェーズ手順を
   すべて内包。1ファイルで完結するが長大化し、フロー変更のたびにエンジン本体を編集（保守性最低）。
2. **各コマンド自走リレー方式（B）** — 各フェーズコマンドが自走時に次を自動起動。連結ロジックが
   多数のコマンドに分散コピーされ、貼り忘れ＝連結断絶リスク。
3. **宣言的フロー定義方式（C）** — フロー定義（`rules/autorun-flow.md`）・インタープリタ
   （`commands/autorun.md`）・実行部品（既存コマンド/スキル）の3層分離。

（A/B/C は設計探索ワークフローで採点し、保守性・既存整合・coding-style 適合で C が最高評価。）

## 決定

**選択肢 C（宣言的フロー定義方式）を採用する。**

- `rules/autorun-flow.md` = フローの「形」（モード表・遷移表・関門・success_test）の単一の正。
- `commands/autorun.md` = それを解釈するインタープリタ（ステートマシン）。
- 既存コマンド/エージェント/スキル = フェーズ実行の部品（再利用、停止設計は単発時のまま）。
- **RUN_STATE は会話内の transcript 変数**で持つ（ランタイム不在のため。`commands/review-loop.md`
  と同型の親オーケストレータ状態保持方式）。
- 関門停止は **宣言(kind=gate)・制御(autorun 手続き)・物理(hooks)** の独立3層で担保する。
  ただし物理層（`pr-base-checker.py` 等）は git/Bash 経由の push/PR にのみ作動し、デプロイ操作や
  MCP 経由には作動しない（過大表示しない。push/PR は gh CLI 経由に限定する）。
- 機械検証可能性は起動時に前倒し検証する（不能なら自走不可で早期停止）。

### commit の扱い（git-workflow.md との両立）

ADR-007 で commit は「可逆なので関門にしない（kind=auto）」とした。一方グローバルルール
`rules/git-workflow.md` は「コミット前に承認・Never commit silently」を全エージェントに強制する。
両立のため、**`/autorun` 起動時に「自走中の自動コミットを許可する」包括承認を利用者から1回取得**し、
それを以後の自動コミットの根拠とする（メッセージは毎回 transcript に提示）。包括承認が得られなければ
commit を gate 扱いにする。この例外を `git-workflow.md` に明記する。

## 結果

### Positive

- 保守性が最も高い（フェーズ順序・関門の増減・新モード追加が autorun-flow.md の表1行で済む）。
- coding-style の「小ファイル・高凝集低結合」に最も合致。
- 既存資産（コマンド/エージェント/hooks/loop-safety/memory）を部品として再利用、新概念が最小。
- 既存コマンドの停止設計を大きく変えずに済む（autorun が kind を制御するため）。

### Negative

- 連結の確実性は最終的に Claude のルール遵守に依存（ランタイム強制なし）。重大事故（本番デプロイ・
  main 直 PR・破壊操作）は検証済みの hooks が物理層でブロックするため信頼性の下限は担保される。
- commit 包括承認は git-workflow.md のグローバル規律に対する自走時例外であり、運用上の周知が要る。

## 関連

- `docs/adr/007-autonomous-loop-execution.md` — 関門4点・自動連結の決定（本 ADR の前提）
- `rules/autorun-flow.md` — フロー定義 / `commands/autorun.md` — インタープリタ
- `rules/loop-safety.md` — 安全規律の正本 / `rules/git-workflow.md` — commit 包括承認の例外
