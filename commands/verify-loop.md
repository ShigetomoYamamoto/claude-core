---
name: 検証ループ
description: |
  コード変更を「レビュー→指摘の独立検証→修正→再レビュー」と、
  CRITICAL/HIGH が 0 になるか上限到達まで自律で回します（Workflow 使用）。
---

# /verify-loop — 自律検証ループ

`code-reviewer` / `security-reviewer` の「CRITICAL が 0 になるまで繰り返す」を、人間の判断を挟まずに回す。検出 → 検証 → 修正を `Workflow` のパイプラインで自律実行する。

## 前提（loop-safety.md 準拠）

- 専用ブランチで作業していること（`main` / `master` / `develop` 不可）
- ハードストップ: **デフォルト最大5ラウンド**。未指定ならこの上限で合意を取る
- 成功は機械的に判定する: 「CRITICAL=0 かつ HIGH=0、かつ テスト / lint / 型チェックが pass」

## ループ構造（Workflow）

各ラウンドで以下を回す:

1. **Review（検出）** — 変更ファイルを `code-reviewer` と `security-reviewer` で並列レビューし、指摘を severity 付きで集約する。
2. **Verify（検証）** — 各 CRITICAL / HIGH 指摘を独立エージェントで**反証的に**検証する（「本当に問題か / 誤検知では」）。過半数が「実在」とした指摘だけ残す。
3. **Fix（修正）** — 残った指摘を最小差分で修正する（build-error-resolver の方針）。
4. **再判定** — テスト / lint / 型チェックを実行する。

## 終了条件（いずれか）

- CRITICAL=0 かつ HIGH=0 かつ 機械チェック pass（成功）
- ラウンド上限到達（未達 → 残指摘を報告して停止）
- 2ラウンド連続で新規指摘ゼロかつ未修正が残る（膠着 → 報告して停止）

## 不可逆操作

- このループ内では commit / push を行わない。終了後に通常の `/commit` → `/create-pr` へ渡す。

## 関連

- `rules/loop-safety.md` — ハードストップとゴールドリフト対策
- `rules/memory.md` — 2回出た指摘は memory に昇格させ再発を止める
- `agents/code-reviewer.md` / `agents/security-reviewer.md` — 検出・検証に使うエージェント
