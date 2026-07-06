# ADR-022: autorun フロー定義を常時ロード規範（rules/）からオンデマンド参照（docs/）へ移す

**ステータス**: accepted

**日付**: 2026-07-06

## コンテキスト

`~/.claude/rules/` 配下の Markdown は**毎セッション・全ファイルが自動ロード**される（公式仕様。サブディレクトリも再帰的に対象）。2026-07-06 のナレッジベース棚卸しで、常時ロード合計 821 行のうち `rules/autorun-flow.md` が 203 行（約25%）を占める一方、その内容は `/autorun` 実行時にしか使われず、しかも `commands/autorun.md` はステップ4で毎イテレーション同ファイルを明示的に Read する設計であることが判明した。つまり常時ロードは純粋な二重コストになっていた。

[ADR-008](./008-orchestration-declarative-flow.md) は「フロー定義＝`rules/autorun-flow.md` が単一の正」と置き場所まで含めて決定していたため、移動には本 ADR を要する。

制約: 移動先は任意のプロジェクトから固定パスで参照できる必要がある（`/autorun` はどのプロジェクトでも動く）。`~/.claude` に symlink される静的ディレクトリ（[ADR-009](./009-symlink-and-settings-merge.md)）に含まれない場所へ移すと、ランタイムで到達できなくなる。

## 検討した選択肢

1. **現状維持** — 毎セッション 203 行の固定コストを払い続ける。
2. **`rules/reference/` サブディレクトリへ移動** — 不成立。公式仕様で rules/ はサブディレクトリも再帰的に常時ロードされる（`paths` frontmatter が無い限り）。
3. **`paths` frontmatter による条件付きロード化** — 「特定ファイルを触るときだけ適用」の仕組みであり、「/autorun 実行時のみ」を表すパスパターンは存在しない。マッチしないダミーパターンは仕組みの目的外利用で、将来の読み手を誤らせる。
4. **`docs/autorun-flow.md` へ移動し、`docs/` を install.py の symlink 対象に追加（採用）** — 常時ロード対象外になり、`~/.claude/docs/autorun-flow.md` として全プロジェクトから到達できる。副次効果として `docs/adr/*` 等の参照文書もランタイムで解決可能になる。

## 決定

**選択肢4を採用する。**

- `rules/autorun-flow.md` → `docs/autorun-flow.md` へ移動（内容・正本性は不変）。
- `install.py` の symlink 対象静的ディレクトリに `docs` を追加する（ADR-009 の方式の適用範囲拡張）。
- 参照元（commands/autorun.md・commands/plan.md・rules/loop-safety.md・rules/agents.md・skills/loop-engineering/SKILL.md・agents/architect.md・agents/rollback-runner.md・README.md・docs/architecture.md・docs/requirements.md）のパスを更新する。**既存 ADR 本文中の旧パス表記は歴史記録として残す**（ADR は書き換えない。[ADR-008](./008-orchestration-declarative-flow.md) にのみ注記を追記）。
- ADR-008 の決定のうち**置き場所のみ**を本 ADR が置き換える。宣言的フロー定義・3層分離・「フロー定義が単一の正」は不変。

## 結果

### Positive

- 毎セッションの常時ロードが 821 行 → 約605 行（約26%減。同時に削除した `rules/patterns.md` 13行を含む）。
- `/autorun` の動作は不変（元々ランタイムに都度 Read しており、参照パスが変わるだけ）。
- `~/.claude/docs/` が生まれ、ADR 等の参照文書にどのプロジェクトからも到達できる。

### Negative

- 既存マシンは `git pull` 後に **`./setup.sh` の再実行が1回必要**（`~/.claude/docs` symlink の新設。ADR-009 の「settings/mcp 変更時のみ再実行」に docs 追加時が加わる）。
- 「rules/ を見ればフローも載っている」という発見性は下がる（README とコマンド側の参照で緩和）。
- `docs/` symlink という自前配線が1つ増える。

## 関連

- [ADR-008](./008-orchestration-declarative-flow.md) — 宣言的フロー定義（置き場所のみ本 ADR が改定）
- [ADR-009](./009-symlink-and-settings-merge.md) — symlink 方式（docs を対象に追加）
- `docs/autorun-flow.md` — 移動後の実体 / `install.py` — symlink 実装
- 2026-07-06 ナレッジベース棚卸し（本 ADR の発端）
