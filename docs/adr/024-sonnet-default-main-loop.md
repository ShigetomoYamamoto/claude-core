# ADR-024: モデル役割の既定を反転する — 主ループは Sonnet、Opus/Fable はエスカレーション専用

**ステータス**: Accepted

**日付**: 2026-07-22

**部分的に置き換える対象**: [ADR-016](./016-opus-execution-guard.md) / [ADR-020](./020-thinking-tier-execution-guard.md)（「思考ティアが主ループを担う」前提の記述を、本 ADR の既定反転で更新。ガード機構そのものは不変）

> **注記（2026-08-09）**: 上記の「ガード機構そのものは不変」は [ADR-026](./026-execution-guard-role-axis.md) で覆った。既定が Sonnet になった結果ガードが通常運転で発火しなくなっていたため、判定軸をモデルから役割へ変更した。

## コンテキスト

ADR-016 / ADR-020 は「思考ティア（Opus/Fable/Mythos）が主ループを担い、実行系操作は
Sonnet/Haiku へ委譲する」前提で `hooks/opus-execution-guard.py` を設計した。

直近7日間の実測（[Issue #82](https://github.com/ShigetomoYamamoto/claude-core/issues/82)）:
- 思考ティア主ループの論理ターン数: 週1,905（Opus4.8=1,308 / Fable5=381 / Opus4.7=216）。
- 無作為サンプル(n=50)の定性分類: SONNET_OK 82% / NEEDS_OPUS 14%（下限）/ OTHER 4%。
- モデル別 NEEDS_OPUS: Opus4.8=20.6% / Fable5=0%(0/10) / Opus4.7=0%。
- Anthropic 一次情報（2026-07-22 確認）: Team プレミアムシートは週次共有プール＋5時間枠が単一で、
  Opus 専用枠のような分離はない。Fable 5 はプラン込みだが他モデルより速くプールを消費する。

**解釈**: Opus は取り次ぎ役ではなく、主ループ仕事の約8割は Sonnet で一気通貫可能。Fable は
過剰使用気味。共有プールである以上「安い方（Sonnet）に寄せれば常に有利」で場合分けは不要。

**限界**: n=50・95%CI 約±10pt・NEEDS_OPUS は下限（真値はやや高い可能性）・単一評価者。この
限界により「Sonnet 一辺倒」にはせず、明示的なエスカレーション条件を残す（下記）。

## 検討した選択肢

1. **現状維持（思考ティア主ループ既定のまま）** — 実測と反する。週次クォータ逼迫の主因を放置する。
2. **Sonnet 完全一辺倒（エスカレーション廃止）** — NEEDS_OPUS が下限推定である以上、アーキ判断・
   曖昧要件解決などで質が落ちるリスクを無視することになる。限界を無視した過剰反応。
3. **既定を Sonnet 主ループへ反転し、Opus/Fable は明示条件でのみ呼ぶエスカレーション先とする（採用）** —
   実測(82% SONNET_OK)と限界(NEEDS_OPUS 下限)の両方を反映できる。

## 決定

**選択肢3を採用する。**

### 1. 既定モデルの反転

主ループの既定を **Sonnet** とする。Opus/Fable は以下の **5条件のいずれか**に該当する場合のみ
呼び出すエスカレーション先とする（`rules/role-separation.md` に明文化・常時ロード）:

- 曖昧要件の解決
- アーキテクチャ・基盤判断
- 非自明・プラットフォーム依存のリスク
- 破壊的操作前の制約確認
- 重要変更の最終承認

Fable はさらに一段厳しいバー（分割不能・全体を単一コンテキストで見る必要・最大深度が要る）で、
Opus のデフォルト代替ではなく Opus からのさらなるエスカレーション先とする。

### 2. maker≠checker の維持

重要変更は独立レビュー（別 Sonnet セッション、または Opus）を経る。`rules/safety-irreversible.md`
の既存原則を維持し、本 ADR では新設しない（`rules/role-separation.md` から参照のみ）。

### 3. エフォート方針（ティア別、`rules/claude-efficiency.md` に追記）

- メインチャット（対話・グローバル `/effort`）: 既定 **high**。Opus/Fable でのエスカレーション作業
  そのものに限り xhigh/max へ引き上げる。
- サブエージェント: per-agent frontmatter `effort:` で指定（実装は claude-engineering 側）。
  判断系=xhigh／レビュー=high／実行=medium〜high／doc=low／Fable相当=max。
- 補足: per-agent の `model:`/`effort:` は frontmatter がネイティブサポートし、hook からは変更できない。

### 4. `hooks/opus-execution-guard.py` の再定義 — 判定ロジックは不変、フレーミングのみ更新

検証の結果、**ガードの判定ロジックは既定反転の影響を受けない**: Sonnet は反転前から実行可能
だったし反転後も変わらず実行可能。Opus/Fable/Mythos は反転前から実行ブロック対象だったし
反転後も変わらずブロック対象。「主ループが Sonnet か思考ティアか」ではなく「今アクティブな
モデルが思考ティアか」だけで判定しており、この判定基準自体に既定の反転が影響しない。

変更したのは **docstring とブロック時メッセージの文言のみ**（判定関数・正規表現・
`is_thinking_model`・`agent_id` ゲート・fail-open は無変更）:
- 「メインループの思考ティアモデル」→「メインループが思考ティアモデルにエスカレーション中」の
  フレーミングへ。ガードは「思考ティア主ループの事故防止」ではなく「エスカレーション後の
  Sonnet への実行引き戻し」を強制する安全網として説明する。
- ブロック時メッセージに ADR-024 の参照を追加。
- `hooks/test_opus_execution_guard.py` のメッセージ文字列アサーションを追従。ロジックのテストは
  無変更（全33件 pass 確認済み）。

hook ファイル名は変更しない（ADR-020 と同じ理由: settings 配線の安定を優先）。

## 結果

### Positive

- 実測(82% SONNET_OK)に沿って週次/5時間枠のクォータ逼迫を緩和できる。
- エスカレーション条件を明文化することで「Sonnet 一辺倒」による質低下(NEEDS_OPUS 下限14%)を防ぐ。
- ガード機構(hook)を作り直さずに済み、動作確認済みのテストスイートをそのまま維持できる。
- maker≠checker・fail-open・agent_id ゲートなど既存の安全設計は無傷。

### Negative（限界を正直に）

- n=50・単一評価者の分類に基づく決定であり、NEEDS_OPUS の真値はサンプルより高い可能性がある。
  エスカレーション条件の運用実態は今後の棚卸し（memory-dream 等）で再検証が要る。
- エスカレーション条件（5項目）の判定はモデル・規範任せであり、hook のような機械的強制はない
  （「曖昧要件」「非自明なリスク」は自動検知できないため）。
- Fable のプール消費速度は Anthropic 側の運用に依存し、本 ADR が直接制御できない外部要因。

## 関連

- [ADR-016](./016-opus-execution-guard.md) — 元のガード決定（本 ADR がフレーミングを更新、ロジックは維持）
- [ADR-020](./020-thinking-tier-execution-guard.md) — 思考ティア判定の拡張（Fable/Mythos 追加、維持）
- [ADR-006](./006-hook-error-policy.md) — fail-open 原則（維持）
- `rules/role-separation.md` — 既定反転・エスカレーション5条件・Fable の追加バーを明文化
- `rules/claude-efficiency.md` — モデル選択順序の反転・エフォート方針の追記
- `rules/safety-irreversible.md` — maker≠checker（既存原則を参照のみ、新設なし）
- `hooks/opus-execution-guard.py` / `hooks/test_opus_execution_guard.py` — 文言更新、ロジック不変
- 連動: claude-engineering 側 Issue（loop-engineering / 実行系エージェントの整合）→
  https://github.com/ShigetomoYamamoto/claude-engineering/issues/10
