# ADR-031: settings.json の hook 配線マージを「所有 hook の入れ替え」に変える

**ステータス**: accepted

**日付**: 2026-10-02

## コンテキスト

- [ADR-009](./009-symlink-and-settings-merge.md) の FORCE 規則により、`hooks.PreToolUse` / `PostToolUse` は fragment の内容で**配列ごと**置き換えていた（`installer.py` の `_FORCE_HOOK_EVENTS`）。
- [ADR-027](./027-rename-execution-guard.md) は、hook を改名したときに旧パスが live に残らないことを、この置き換えに依存して保証していた。
- 2026-10-01、update の dry-run で、Orca が追加した `matcher: "*"` の2項目（PreToolUse / PostToolUse）が消えることが分かった（#118）。ADR-009 は「live のキーは決して削除しない」としているが、置き換えの単位がキーではなく配列なので、他ツールの項目まで消えていた。
- 回避策として、settings.json を退避してから install し、書き戻す作業を手で行っていた。
- `installer.py` は claude-core / claude-engineering / claude-work-agent の3リポジトリで同一ファイルなので、3つとも同じ挙動だった。

## 決定

- FORCE 対象のイベント（PreToolUse / PostToolUse）では、配列丸ごとではなく、**この pack が所有する hook だけ**を fragment の内容に入れ替える。
- 所有の定義: hook の `command` を `shlex` で分割したトークン（`~` は展開する）のいずれかが `<target>/<rel>` と完全一致するもの。`rel` は「今回配布するファイル」と「前回の manifest に記録されたファイル」の和集合とする。
  - 前回の manifest を含めるのは、改名や削除で配布しなくなった旧ファイルを指す項目も所有とみなし、除去するため（ADR-027 の前提を維持する）。
  - 「`<target>/hooks/` 配下かどうか」では判定しない。他ツールが同じディレクトリに置いた hook（herdr の `.sh` など）を巻き込むため。
  - 部分文字列では判定しない。`foo.py` と `foo.py.bak` を取り違えるため。
- 判定は matcher グループ単位ではなく、グループ内の hook 1本単位で行う。所有 hook を取り除いて空になったグループは削除し、他の hook が残るグループはそのまま残す。
- 並び順は「fragment のグループ → 残った他ツールのグループ（元の順）」とする。続けて2回実行しても結果は変わらない。
- 判定できないとき（`shlex` が分割に失敗したときなど）は、他ツールの項目として残す。消しすぎるより、残しすぎる側に倒す。
- fragment にそのイベントのキーが無ければ、live をそのまま残す（従来どおり）。fragment が空配列なら、所有 hook だけがすべて消える。
- あわせて、`__pycache__/` と `*.pyc` を配布対象から外す。gitignore 全般を尊重する汎用化はしない（untracked のファイルも配布するのは仕様）。
- dry-run では、従来のマージ後 JSON の全文に加えて、live との unified diff を出す。削除される項目が見えるようにするため。

## 結果

### Positive

- Orca など、hook を自分で追加するツールの設定が install / update で消えなくなる。退避と書き戻しの手作業が不要になる。
- 改名・削除した hook の旧配線は、引き続き除去される。
- dry-run で、削除される項目を事前に確認できる。

### Negative

- 所有の判定は command 文字列のトークン一致に依存する。core の hook の command を手で書き換えて別のパス表記にした場合は、所有とみなされずに残り、fragment の項目と二重になりうる。
- manifest が無い状態（初回 install、manifest の破損）では、配布しなくなった旧ファイルを指す項目を所有と判定できず、残る。

## 関連

- [ADR-009](./009-symlink-and-settings-merge.md) — settings.json の FORCE / DEFAULT マージ。本 ADR は hooks の FORCE の意味を変更する。
- [ADR-027](./027-rename-execution-guard.md) — 改名時に旧パスを残さない前提。本 ADR 以降は前回 manifest に基づく所有判定で維持する。
- #118 — 本 ADR のきっかけとなった Issue。
