# claude-core

> **本リポジトリは claude-core foundation です（[ADR-023](./docs/adr/023-three-foundation-split.md)）。**
> 単一のグローバル設定を **core / engineering / work-agent** の3つの独立 foundation に分割した結果、
> このリポジトリはドメイン中立な部分（安全ガード・役割分離・メモリ運用など）のみを残した **claude-core** です。
> - インストール先は `~/.claude` のみ。**symlink ではなく copy 型インストーラ**（`installer.py` + `install.py`）で導入します。
> - グローバル MCP・開発/業務プラグインは持ちません。
> - 開発ワークフロー一式（エージェント・コマンド・git hook 等）は別リポジトリ **claude-engineering** へ、業務/運用ワークフローは **claude-work-agent** へ移動しました（プロジェクトへ個別インストール。詳細は [`docs/migration/inventory.md`](./docs/migration/inventory.md)）。

Claude Code 全体で共通のドメイン中立な振る舞い規範・安全装置を提供する dotfiles リポジトリ（claude-core foundation）。

新しいマシンで `python3 install.py` を実行するだけで、ドメイン中立な `rules/` `hooks/` `skills/` が `~/.claude` に導入されます。開発ワークフローの自走基盤（要件→設計→実装→PR→デプロイの自動連結）は別リポジトリ **claude-engineering** が提供します。

> 設計の背景や判断理由は [`docs/requirements.md`](./docs/requirements.md)（要件定義）、[`docs/architecture.md`](./docs/architecture.md)（アーキテクチャ）、[`docs/adr/`](./docs/adr/)（設計判断記録）を参照してください。

## 設計方針

**グローバル（claude-core、このリポジトリ）** と **プロジェクトローカル（claude-engineering / claude-work-agent）** で役割を分離しています。

| 層 | 場所 | 内容 |
|---|---|---|
| グローバル | `~/.claude/`（claude-core） | ドメイン中立・全プロジェクト共通の安全装置・振る舞い規範 |
| プロジェクトローカル | `<project>/.claude/`（claude-engineering または claude-work-agent） | 開発ワークフロー一式、または業務/運用ワークフロー一式 |

engineering・work-agent はそれぞれ対象プロジェクトへ個別インストールする（1プロジェクト=1ドメイン。[ADR-023](./docs/adr/023-three-foundation-split.md)）。

## 含まれるもの（claude-core、ADR-023 後の構成）

| ディレクトリ/ファイル | 内容 |
|---|---|
| `hooks/` | ドメイン中立の安全装置（シークレット検出・秘匿ファイルのステージ防止・doc 生成ブロック・大量削除確認・opus-execution-guard） |
| `rules/` | ドメイン中立の運用ルール（answer-only・collaboration-style・claude-efficiency・memory・role-separation・safety-irreversible・secret-hygiene） |
| `skills/` | ドメイン中立スキル（3-line-contract, memory-dream） |
| `docs/` | 要件定義・アーキテクチャ・ADR・移行資料（`docs/migration/`） |
| `installer.py` / `install.py` | copy 型インストーラ本体（manifest ベース。symlink は使わない。`--dry-run` / `verify` / `uninstall` 対応） |
| `settings-fragment.json` | core が配線する hook のみを含む settings 断片（`__TARGET__` を解決してマージ） |
| `tests/` | インストーラの単体テスト |

> 「agents/」「commands/」「workflows/」「templates/」「mcp.json」「settings.json.template」「setup.sh」は
> claude-engineering（一部は claude-work-agent）へ移動済みで、このリポジトリには存在しません
> （[`docs/migration/inventory.md`](./docs/migration/inventory.md) 参照）。

## 開発・業務ワークフロー

開発ワークフロー（要件定義・設計・実装・TDD・レビュー・PR・デプロイ・ループ自走 `/autorun` 等）は
このリポジトリではなく別リポジトリ **claude-engineering** が提供する。業務/運用ワークフローは
**claude-work-agent** が提供する。いずれもグローバルではなく、対象プロジェクトへ個別インストールする
（1プロジェクト=1ドメイン。[ADR-023](./docs/adr/023-three-foundation-split.md)）。

claude-core はこれら2つの foundation が乗る土台（ドメイン中立の安全装置・振る舞い規範）のみを提供する。

## settings-fragment.json の主な設定

- `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: "1"` — 複数エージェントの並列実行を有効化
- `permissions.defaultMode: "auto"` — ほとんどの操作を自動承認
- フック: PreToolUse（opus-execution-guard・doc-blocker・mass-delete-blocker・git-add-secret-blocker）、PostToolUse（secret-detection）
- `install.py` が `__TARGET__` を実パスへ解決したうえで `~/.claude/settings.json` へキー単位マージする（live の個人設定・他 foundation の配線は上書きしない）

git/gh 権限や開発/業務プラグインの有効化は claude-engineering / claude-work-agent 側の settings-fragment が持つ（core は持たない）。

## 新しいマシンへのインストール

### 前提条件

| ツール | 最低バージョン | 備考 |
|---|---|---|
| python3 | 3.8+ | `install.py`（インストーラ本体）と hook 用 |
| git | 2.0+ | |

対応 OS: macOS / Linux（Windows 非対応）

> GitHub MCP・公式プラグイン等の開発ツール連携は claude-engineering 側が管理する（core はグローバル
> MCP・プラグインを持たない。[ADR-023](./docs/adr/023-three-foundation-split.md)）。

### インストール（ADR-023 以降: copy 型・symlink 廃止）

```bash
git clone https://github.com/ShigetomoYamamoto/claude-core.git ~/dotfiles/claude-core
cd ~/dotfiles/claude-core
python3 install.py --dry-run   # 変更計画を確認（書き込みなし）
python3 install.py             # 適用（既定ターゲットは ~/.claude）
```

`install.py`（実体は `installer.py` の薄いラッパー）が `rules/`, `hooks/`, `skills/` を
`~/.claude/` に **コピー**し、`<target>/.claude-core.manifest.json`（管理ファイル一覧 +
sha256）を書きます。symlink は使いません。`settings-fragment.json` の hook 配線を
`~/.claude/settings.json` へキー単位マージします（`__TARGET__` を実パスに解決。live の
個人設定は上書きしない）。

```bash
python3 install.py verify      # manifest とハッシュの整合を確認
python3 install.py uninstall   # manifest 内・ハッシュ一致ファイルのみ削除（backup を残す）
```

> 旧 symlink 方式（`setup.sh` / `mcp.json` / `settings.json.template` による全体マージ）は
> retired です（[ADR-023](./docs/adr/023-three-foundation-split.md)）。

## 別マシンで最新の設定を取得するとき

`rules/` `hooks/` `skills/` は copy インストールのため、repo を更新しただけでは `~/.claude/` に反映されません。`git pull` の後に `python3 install.py`（update）を再実行してください。

```bash
cd ~/dotfiles/claude-core
git pull
python3 install.py --dry-run   # 変更計画を確認（書き込みなし）
python3 install.py             # 反映
```

## 拡張方法

新しい hook を追加する手順です。`agents/` `commands/` `workflows/` `templates/` `mcp.json` の追加手順は claude-engineering 側のドキュメントを参照してください（core はこれらを持たない）。

### 新 hook を追加

1. `hooks/<name>.py` を作成（100 行以下・単一責務）
2. `settings-fragment.json` の `hooks` セクションに配線追加（`__TARGET__` はインストール時に実パスへ解決される）
3. コミット → 対象マシンで `git pull && python3 install.py`（copy インストールのため再実行が必要）

設計原則：

- 予期せぬエラーは `exit 0`（Claude を止めない）
- 意図的ブロックのみ `exit 2`
- ネットワーク通信禁止（ローカル処理のみ）
