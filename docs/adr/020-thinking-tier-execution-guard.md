# ADR-020: 実行ガードの対象を「思考ティア」モデル（Opus / Fable / Mythos）へ拡張する

**ステータス**: accepted

**日付**: 2026-07-04

**部分的に置き換える対象**: [ADR-016](./016-opus-execution-guard.md)（ガード対象を Opus のみとしていた点）

## コンテキスト

[ADR-016](./016-opus-execution-guard.md) は「思考モデルは実行しない」を機械的に強制するため、`hooks/opus-execution-guard.py` でメインループの Opus（`claude-opus-*` 前方一致）の Edit/Write/変更系 Bash をブロックした。

その後 Anthropic が Claude 5 ファミリー（Mythos クラス: Fable 5 = `claude-fable-5`）を提供し、本環境の既定モデルも Fable 5 になった。Fable は Opus より上位の「思考」モデルだが、ガードの判定が `claude-opus-*` 前方一致のみのため、**Fable のメインループは一切ブロックされず（fail-open）**、役割分離（`rules/role-separation.md`）の物理層が実質無効化されていた。2026-07-04 のナレッジベース棚卸し（memory-dream）で発見。

## 検討した選択肢

1. **何もしない（規範のみで運用）** — Fable での「ついうっかり編集」を止められず、ADR-016 の目的（機械的強制）が果たされない。
2. **hook を「Sonnet/Haiku 以外は全ブロック」の allowlist 方式へ反転** — 未知の将来モデルに強いが、判定不能時に fail-closed へ倒れやすく [ADR-006](./006-hook-error-policy.md)（fail-open）と衝突。誤ブロックによる開発全停止リスク。
3. **ブロック対象 prefix に思考ティア（`claude-fable-*` / `claude-mythos-*`）を追加（採用）** — ADR-016 の denylist 設計・fail-open を維持したまま、対象を現行の思考ティアへ拡張。hook のファイル名（`opus-execution-guard.py`）は settings 配線の安定のため変更しない。

## 決定

**選択肢3を採用する。** `is_opus()` を `is_thinking_model()`（`claude-opus-` / `claude-fable-` / `claude-mythos-` 前方一致）へ拡張する。agent_id ゲート（サブエージェント無条件許可）・fail-open・Bash denylist の設計は ADR-016 のまま不変。hook のファイル名・settings 配線も不変。

「思考ティア」の定義: 役割分離で「実行させない」側に置くモデル群。現行は Opus / Fable / Mythos。新しい思考ティアのモデルファミリーが出たら prefix を追加する(この追随コストが denylist 方式の保守費であり、allowlist 反転をしない対価として引き受ける)。

## 結果

### Positive

- Fable 既定の環境でも役割分離の物理層が回復する（「ついうっかり編集」を機械的に止められる）。
- ADR-016 の設計（fail-open・agent_id ゲート・denylist）と settings 配線を変えずに済む。

### Negative

- 新モデルファミリー登場のたびに prefix 追加が要る（追随漏れが再発しうる。定期棚卸しで検出する）。
- hook 名が `opus-execution-guard` のまま実対象より狭い名前になる（配線安定を優先した対価）。

## 関連

- [ADR-016](./016-opus-execution-guard.md) — 元の決定（本 ADR が対象範囲を拡張）
- [ADR-006](./006-hook-error-policy.md) — fail-open 原則（維持）
- `rules/role-separation.md` / `rules/claude-efficiency.md` — ティア表記の更新
- `hooks/opus-execution-guard.py` / `hooks/test_opus_execution_guard.py` — 実装とテスト
