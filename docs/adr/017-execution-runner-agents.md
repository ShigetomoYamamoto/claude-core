# ADR-017: 実行役レイヤーの拡充 — git-runner と executor で fixer 偏重を解消する

**ステータス**: accepted

**日付**: 2026-06-24

## コンテキスト

[ADR-016](./016-opus-execution-guard.md) でメインループの Opus の編集系ツール・変更系 Bash を Hook でブロックし、実行は Sonnet/Haiku に委譲する方針にした。その結果、実装中の実行委譲が `fixer` に集中し(コミット / push / PR / マージ / doc の英語化)、`fixer` 本来の charter(レビュー指摘の修正)を逸脱した。

原因は、既存エージェントが「思考の専門家」軸で分割されており、**実行そのものを担う汎用役が不在**だったこと。特に2領域に受け皿が無い:
1. VCS/リリース操作(stage/commit/push/PR/branch/merge)
2. どの専門家の管轄にも入らない汎用の編集/Bash(設定ファイル・スクリプト・ファイル操作)

### 検証済みの事実

- 組み込み `general-purpose` を Task 起動して変更系 Bash を実行 → ブロックされない(サブエージェントは stdin に `agent_id` が付き、ガードの `agent_id` ゲートを通過する)。**ただし `general-purpose` / `claude` は親(Opus)モデルを継承するため、委譲しても「Opus が高コストで実行」する形になり、役割分担・コスト的に不適**。
- サブエージェントは生の `git`/`gh` を直接実行でき、コミット規約・PR base・秘匿ファイルの規約は hooks(`commit-msg-convention` / `pr-base-checker` / `git-add-secret-blocker` / `git-destructive-blocker`)が機械的に担保する。スラッシュコマンドをサブから呼ぶ必要はない。

## 検討した選択肢

1. **1つの汎用実行役に統合** — 却下。charter が広すぎて再び「何でも屋」化し、`fixer` 偏重と同じ構造を別名で作るだけ。
2. **組み込み `general-purpose` を直接使う** — 却下。親(Opus)モデルを継承し高コスト・役割不適(検証済み)。使うなら Task で `model: sonnet` を明示する必要があり、忘れやすい。
3. **既存エージェントの charter を拡張(`fixer` に VCS を足す等)** — 却下。後方互換と単一責務を崩す。`fixer` はレビュー修正専用のまま据え置く。
4. **(採用)専用 Sonnet 実行役を2つ新設** — `git-runner`(VCS/リリース)と `executor`(専門家管轄外の残余)。境界をエージェント単位で分離する。

## 決定

1. **`git-runner`**(`model: sonnet`、tools: Bash/Read/Write/Grep/Glob)を新設。規約ロジックは再実装せず、hooks と既存コマンド(`/create-branch`・`/create-pr`・`/commit-commands:commit`)に委ねる。承認は呼び出し元が事前取得済みである前提で機械実行に徹し、push/PR の承認は省略しない。
2. **`executor`**(`model: sonnet`、フル tools)を新設。本文最上位の charter 境界表で専門家の管轄を最初に振り分け、残余だけを実行する。
3. doc 散文は `doc-updater` を優先。`fixer` は据え置き(charter 変更なし)。
4. `general-purpose` / `claude` は実行委譲では非推奨(Opus 継承で高コスト)。使うなら `model: sonnet` を明示。
5. ルーティング(`rules/agents.md` の proactive 表、`rules/role-separation.md` の委譲リスト)へ反映。

## 結果

### Positive

- `fixer` の charter 純度を回復(レビュー修正専用に戻る)。
- Opus の実行委譲に明確な受け皿(VCS=git-runner / 残余=executor)ができる。
- 役割分離([ADR-016](./016-opus-execution-guard.md))が運用で機能する。
- 規約の単一の正(hooks + 既存コマンド)を維持し、二重定義を作らない([ADR-014](./014-loop-engineering-as-discipline.md))。

### Negative

- エージェント数が増え、委譲先の選択肢が増える(`executor` の境界表で緩和)。
- `executor` の「残余」判定は LLM 判断に依存する(境界表の明文化で緩和)。
- `git-runner` の物理層は Bash 経路のみ(MCP 経由 PR には作動しない)。過大に主張しない([ADR-014](./014-loop-engineering-as-discipline.md))。

## 関連

- [ADR-016](./016-opus-execution-guard.md) — 本 ADR の前提(Opus 実行ガード)
- [ADR-014](./014-loop-engineering-as-discipline.md) — 物理層スコープ・二重定義回避
- [ADR-012](./012-official-plugins-for-git-review-security.md) — 公式委譲・自作コマンド維持の方針
- [ADR-003](./003-language-policy.md) — 言語ポリシー(rules・agents は英語)
- `rules/role-separation.md` / `rules/agents.md` — ルーティングの正
- `agents/git-runner.md` / `agents/executor.md` — 実装
