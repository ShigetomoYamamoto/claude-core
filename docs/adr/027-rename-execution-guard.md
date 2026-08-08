# ADR-027: 実行ガードの hook ファイル名を役割に合わせて改名する

**ステータス**: accepted

**日付**: 2026-08-09

## コンテキスト

[ADR-026](./026-execution-guard-role-axis.md) で実行ガードの判定軸を「モデル（思考ティアか）」
から「役割（メインループか実行層か）」へ変更し、モデル判定と transcript 読み取りを削除した。
しかしファイル名は `hooks/opus-execution-guard.py` のまま据え置いていた。

このガードはもう Opus とは何の関係もない。[ADR-025](./025-single-entry-and-loop-engineering-skill-retirement.md)
は「名前が実態を僭称すると設計の取り違えを招く」と述べ、`loop-engineering` スキルの改名・廃止に
踏み切っている。同じ問題が実行ガードで起きていた。

## 決定

- `hooks/opus-execution-guard.py` を **`hooks/main-loop-execution-guard.py`** に改名する。
  あわせてテストを `hooks/test_main_loop_execution_guard.py` に改名する。
- `settings-fragment.json` の PreToolUse 配線を新しいパスに更新する。installer の
  `_FORCE_HOOK_EVENTS`（`PreToolUse` / `PostToolUse`）は fragment の内容で live 設定を
  **丸ごと置換**するため、再インストール時に古いパスが残ることはない。
- **既存 ADR（016 / 017 / 020 / 023 / 024 / 026）の本文は変更しない。** 旧ファイル名は
  決定当時の記録として残す（[ADR-022](./022-autorun-flow-out-of-always-loaded-rules.md) の運用）。
  現行の名前は本 ADR と `rules/role-separation.md` を正とする。

## 結果

### Positive

- 名前が判定軸（役割）と一致し、ADR-025 が警戒した「名前による設計の取り違え」を解消する。

### Negative

- **`~/.claude/settings.json` の配線と hook 実体の名前が同時に変わる。** 再インストールが
  中途半端に終わると settings が存在しないパスを指し、`python3 <存在しないファイル>` が
  exit 2 を返すため **PreToolUse が全件ブロック**になる（CLAUDE.md が警告する事故）。
  適用後に「settings.json が参照する全 hook パスが実在すること」を検証する必要がある。
- **claude-engineering 側に旧名の参照が残る。** `agents/executor.md` `agents/git-runner.md`
  `rules/agents.md` ほか複数ファイルが `opus-execution-guard` を名指ししている。これらは
  散文であり実行はされないが、同 foundation は ADR-026 の判定軸変更自体も未反映で、
  `executor` / `git-runner` の `description:` が「思考ティアにエスカレーション中のみ使う」と
  記述している。ガードが全モデルで発火するようになった以上、Sonnet 主ループでブロックされた
  ときに委譲先が名乗り上げない可能性がある。**claude-engineering 側の是正は本 ADR の範囲外の
  未解決課題**であり、判定軸の修正と改名をまとめて行うべきである。

## 関連

- [ADR-026](./026-execution-guard-role-axis.md) — 判定軸の変更。本 ADR はその名前面の追随。
- [ADR-025](./025-single-entry-and-loop-engineering-skill-retirement.md) — 名前が実態を僭称する問題の先例。
- [ADR-022](./022-autorun-flow-out-of-always-loaded-rules.md) — 既存 ADR 本文の旧パス表記を残す運用。
- `rules/role-separation.md` — 現行の名前と役割分担の正本。
