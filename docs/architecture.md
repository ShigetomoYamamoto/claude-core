# claude-core アーキテクチャ

> **本リポジトリは claude-core foundation です（[ADR-023](./adr/023-three-foundation-split.md)）。**
> 単一設定を core / engineering / work-agent の3 foundation に分割した結果、以下は
> claude-core（ドメイン中立・`~/.claude` へ copy インストール・symlink 廃止）のみを
> 記述します。engineering foundation（agents/commands/workflows/templates と対応する
> git hook 群）のアーキテクチャは別リポジトリ側のドキュメントに移動しました
> （[`docs/migration/inventory.md`](./migration/inventory.md) 参照）。

## 概要

claude-core は Claude Code のグローバル設定を管理する dotfiles リポジトリ。「人間の開発業務を Claude Code が肩代わり・サポートする」という上位目的を実現するための土台・基盤を提供する。

詳細な要件は [`requirements.md`](./requirements.md) を参照。

---

## 3レイヤー構造（claude-core、ADR-023 後）

```
┌────────────────────────────────────────────────────────────┐
│                  claude-core（このリポジトリ）               │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Layer 1: Behavior（ふるまいの定義）                  │    │
│  │   rules/   — ドメイン中立の不変ルール（英語）          │    │
│  │   skills/  — ドメイン中立の参照知識                   │    │
│  └────────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Layer 2: Guardrails（受動的な強制）                  │    │
│  │   hooks/    — PreToolUse / PostToolUse               │    │
│  └────────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Layer 3: Installer + Wiring                          │    │
│  │   installer.py / install.py — copy 型・manifest 境界 │    │
│  │   settings-fragment.json    — hook 配線のみ           │    │
│  └────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────┘
                       │ python3 install.py（copy、symlink なし）
                            ▼
┌────────────────────────────────────────────────────────────┐
│                     ~/.claude/                              │
│  rules/ hooks/ skills/ settings.json + .claude-core.manifest.json │
└────────────────────────────────────────────────────────────┘
```

> agents/ commands/ workflows/ templates/ と、それらを対象プロジェクトへ導入する
> `/init-autonomous` は claude-engineering foundation（別リポジトリ、プロジェクト
> ローカルへ個別インストール）に移動しました。旧5レイヤー構成（Workforce /
> Orchestration / Wiring を含む）との対応は [`docs/migration/inventory.md`](./migration/inventory.md) を参照。

---

## 各レイヤーの責務

engineering foundation のレイヤー（Workforce=`agents/`/`commands/`・Orchestration=
`docs/autorun-flow.md`/`workflows/`・Wiring=`mcp.json`/plugins）と、対応する git hook 群
（`protected-branch-edit-guard.py` / `git-destructive-blocker.py` / `pr-base-checker.py` ほか）は
claude-engineering foundation 側のアーキテクチャに移動しました。以下は claude-core 自身が
持つ3レイヤーのみを記述します（[`docs/migration/inventory.md`](./migration/inventory.md) に
資産の分類一覧）。

### Layer 1: Behavior

| ディレクトリ | 責務 | 対象読者 | 言語 |
|---|---|---|---|
| `rules/` | 不変の振る舞いルール。エージェントが必ず守るべき制約 | エージェント（自動参照） | 英語 |
| `skills/` | 再利用可能な参照知識（パターン・サンプル・コマンド例） | エージェント（必要時に参照） | 英語 |

**境界:**
- `rules/` = 「MUST / NEVER / ALWAYS」を含む規範的記述
- `skills/` = 「HOW TO（手順・サンプル）」中心の参照資料
- 同じ内容を両方に書かない。`rules/` から `skills/` を参照する形に統一

### Layer 2: Guardrails

| hook | タイミング | 責務 |
|---|---|---|
| `opus-execution-guard.py` | PreToolUse(Edit/Write/MultiEdit/NotebookEdit, Bash) | 思考ティア（Opus/Fable/Mythos）の編集・変更系 Bash 実行をブロック |
| `doc-blocker.py` | PreToolUse(Write) | 許可リスト外の新規 `.md` / `.txt` 生成を阻止（既存ファイルの編集は許可） |
| `mass-delete-blocker.py` | PreToolUse(Bash) | 再帰削除・大量削除を検知し実行前に確認（ルート/システム相当は決定的ブロック） |
| `git-add-secret-blocker.py` | PreToolUse(Bash) | `git add` による秘匿ファイル（.env/鍵/認証情報）のステージングをブロック |
| `secret-detection.py` | PostToolUse(Edit/Write/MultiEdit) | ハードコードされたシークレットを検出して警告（ブロックはしない・検出層） |

**設計原則:**
- フックは「Claude が忘れたときの保険」
- 単一責務（1 ファイル 1 検査）
- 予期せぬエラーは `exit 0` で Claude を止めない
- 意図的なブロックのみ `exit 2`（`secret-detection.py` は検出のみで exit 2 なし）
- ネットワーク通信禁止・ローカル処理のみ
- 上限 100 行

### Layer 3: Installer + Wiring

| ファイル | 責務 |
|---|---|
| `installer.py` | copy 型インストーラの共通ロジック（install/update/uninstall/verify・manifest 管理・`--dry-run`・backup） |
| `install.py` | `installer.py` を呼ぶ薄いラッパー。claude-core の pack 定義（`managed_paths=["rules","hooks","skills"]`、既定ターゲット `~/.claude`） |
| `settings-fragment.json` | core が配線する hook のみを含む settings 断片（`__TARGET__` を実パスへ解決してキー単位マージ） |

`install.py`（`installer.py` 経由）の責務:

1. `rules/` `hooks/` `skills/` を対象（既定 `~/.claude/`）へ **コピー**（symlink ではない）。
   `<target>/.claude-core.manifest.json` に管理ファイル一覧 + sha256 を記録
2. `settings-fragment.json` を対象の `settings.json` へキー単位マージ（`__TARGET__` を解決。
   live のキーは削除せず、対象の `settings.json` が壊れた JSON の場合はマージをスキップして
   ファイルに触れない）
3. `verify` / `uninstall` は manifest とハッシュの整合で判定し、未知ファイル・ローカル改変
   ファイルには触れない（`uninstall` は backup を残す）

**設計原則:**
- copy 型のため、repo の変更は `git pull` だけでは live へ反映されない。対象マシンで
  `python3 install.py`（update）の再実行が必要
- `settings.json` は実行時に Claude 自身が書くため上書きせずマージ（個人設定・他 foundation の
  配線を保護）
- 破壊的操作の前に必ずバックアップ。`--dry-run` で書き込みなしの事前確認が可能
- すべての操作を idempotent に保ち、何を書いたかを stdout で逐次表示

> 採用方式の変遷は ADR-004（コピー型・superseded）→ ADR-009（symlink + 構造マージ。engineering
> foundation が継承）→ ADR-023（3 foundation 分割・core は copy 型へ回帰）を参照。

---

## 2層境界（グローバル / プロジェクトローカル）

| 層 | 場所 | 内容 |
|---|---|---|
| グローバル | `~/.claude/`（claude-core、このリポジトリ） | ドメイン中立・全プロジェクト共通の安全装置・振る舞い規範 |
| プロジェクトローカル | `<project>/.claude/`（claude-engineering または claude-work-agent） | 開発ワークフロー一式、または業務/運用ワークフロー一式 |

**engineering・work-agent はそれぞれ対象プロジェクトへ個別インストールする**（1プロジェクト=1ドメイン。
ADR-023）。スタック固有の実装（デプロイ先・ビルドコマンド・言語別 hook 等）は engineering 側の
初期化コマンドが生成する（core はこの生成コマンドを持たない）。

---

## 拡張ポイント

claude-core が持つのは `rules/` `hooks/` `skills/` のみ（agents/commands/workflows/templates/MCP
の追加手順は claude-engineering 側のドキュメントを参照。core はこれらを持たない）。新しいマシンへの
導入手順は [README.md](../README.md) の「新しいマシンへのインストール」を参照。

### 新 hook を追加

1. `hooks/<name>.py` を作成（100 行以下・単一責務）
2. `settings-fragment.json` の `hooks` セクションに配線追加（`__TARGET__` はインストール時に実パスへ解決される）
3. コミット → 対象マシンで `git pull && python3 install.py`（copy インストールのため再実行が必要。
   symlink 時代のような即時反映はない）

---

## エラーハンドリング戦略

| 失敗パターン | 期待動作 |
|---|---|
| `settings.json` が JSON として壊れている | マージをスキップし警告を表示。既存ファイルはバイト単位で不変（`installer.py: merge_settings`） |
| manifest（`.claude-core.manifest.json`）が壊れている/読めない | 警告を表示し「未インストール」として扱う |
| hook 内 Python の予期せぬ例外 | 各 hook の設計原則として `exit 0`（Claude を止めない） |
| 意図的なブロック | 各 hook が個別に `exit 2`（doc-blocker・mass-delete-blocker・opus-execution-guard 等。secret-detection は検出のみで exit 2 なし） |
