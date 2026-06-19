# claude-config

Claude Code のグローバル設定を管理する dotfiles リポジトリ。

新しいマシンで `setup.sh` を実行するだけで、AI エージェントが自走して開発を完成させるための共通基盤が整います。

> 設計の背景や判断理由は [`docs/requirements.md`](./docs/requirements.md)（要件定義）、[`docs/architecture.md`](./docs/architecture.md)（アーキテクチャ）、[`docs/adr/`](./docs/adr/)（設計判断記録）を参照してください。

## 設計方針

**グローバル設定（このリポジトリ）** と **プロジェクト設定（`.claude/`）** で役割を分離しています。

| 層 | 場所 | 内容 |
|---|---|---|
| グローバル | `~/.claude/`（このリポジトリ） | スタック非依存・全プロジェクト共通の仕組み |
| プロジェクト | `プロジェクトルート/.claude/` | スタック固有の実装（デプロイ先・ビルドコマンド・言語別 hook） |

プロジェクト側は `/init-autonomous` を実行すると自動生成されます。

## 含まれるもの

| ディレクトリ/ファイル | 内容 |
|---|---|
| `agents/` | 17体のカスタムエージェント（architect, planner, tdd-guide, code-reviewer, reviewer, fixer, requirements-analyst, deploy-runner など） |
| `commands/` | 26個のスラッシュコマンド（/requirements, /design, /plan, /tdd, /commit, /deploy, /autorun, /review-loop, /verify-loop など） |
| `hooks/` | 品質ガード・安全装置（シークレット検出・秘匿ファイルのステージ防止・doc 生成ブロック・保護ブランチ編集ガード・git 破壊操作ブロック・PR base チェック・大量削除確認） |
| `rules/` | コーディングスタイル・テスト・セキュリティ・エージェント運用ルール・Claude 使用効率化・自走/並列/メモリのループ運用ルール |
| `skills/` | 参照スキル（loop-engineering, 3-line-contract, git-workflow, tdd-workflow, security-review） |
| `workflows/` | オーケストレーション用 Workflow テンプレート（loop-engineering-large-A: 大規模Aの計画→赤確認→実装→検証） |
| `docs/` | 要件定義・アーキテクチャ・ADR |
| `settings.json.template` | Claude Code 設定テンプレート（パス自動解決・プラグイン有効化を含む。構造マージのベース） |
| `mcp.json` | MCP サーバー設定（GitHub / Playwright / Figma） |
| `install.py` | インストーラ本体（静的ディレクトリの symlink 化・settings.json の構造マージ・mcp マージ。`--dry-run` 対応） |
| `setup.sh` | `install.py` を呼ぶ薄いラッパー（後方互換用） |

## ループ自走（Loop Engineering）運用

目的を渡せば検証しながら自走する仕組みを、安全装置（`rules/loop-safety.md`）を核に、5層で備えています。

| 層 | 主な成果物 | 役割 |
|----|-----------|------|
| **ミクロ実装** | `skills/loop-engineering/`・`commands/review-loop`（+`reviewer`/`fixer`）・`workflows/loop-engineering-large-A.js` | 1タスクを VISION→テスト→レッド/グリーン→レビュー往復→完了判定で完成させる（強さ A/B/C を自動選択） |
| **マクロ自走** | `rules/autorun-flow`（遷移定義）・`commands/autorun`（解釈）・`docs/adr/007`・`008` | 要件→設計→実装→PR/デプロイを、関門4点（要件・設計・PR・デプロイ）以外を autorun-flow の遷移表に従い自動連結 |
| **安全（横串）** | `rules/loop-safety.md` | 前提条件・ハードストップ・ゴールドリフト・不可逆操作確認（全層が参照する正本） |
| **メモリ（横串）** | `rules/memory.md` | セッションを跨ぐ学習を `memory/` に書き戻す（アウターループ） |
| **並列（横串）** | `rules/parallel-worktree.md` | 並列エージェントが書き込み競合する場合の worktree 分離 |

**安全の原則:** ブレーキ（ハードストップ・専用ブランチ・機械的な成功判定）を先に設定してから自走させる。機械的に成功判定できないタスクは自走させない。

**典型的な使い方:**

```
# 1つのコード実装をクローズドループで完成（ミクロ）
「〜を実装して」と頼むと loop-engineering スキルが強さ A/B/C を自動選択

# 完了条件までフロー全体を自走（マクロ・上限つき）
/autorun tests/ が全 pass し ruff がクリーンになるまで（最大15ターン）

# レビュー→修正を指摘0まで自律で回す
/review-loop      # 通常（Claude が reviewer/fixer を回す）
/verify-loop      # 反証検証つき（自走フローの検証ゲート）
```

## settings.json.template の主な設定

- `defaultMode: auto` — ほとんどの操作を自動承認
- `Bash(git *)` / `Bash(gh *)` — どのプロジェクトでも git/gh 操作が確認なしで動作
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: 1` — 複数エージェントの並列実行を有効化
- `enabledPlugins` — Slack プラグインを自動有効化
- フック: PreToolUse（保護ブランチ編集ガード・doc 生成ブロック・秘匿ファイルのステージ防止・git 破壊操作ブロック・PR base チェック・大量削除確認）、PostToolUse（シークレット検出）、Stop / PermissionRequest（音声通知）

## 新しいマシンへのインストール

### 前提条件

| ツール | 最低バージョン | 備考 |
|---|---|---|
| python3 | 3.8+ | `install.py`（インストーラ本体）と hook 用 |
| bash | 3.2+ | `setup.sh` ラッパー用（`python3 install.py` を直接呼べば不要） |
| git | 2.0+ | |

対応 OS: macOS / Linux（Windows 非対応）

> GitHub MCP は**公式ホスト版リモートサーバー（`https://api.githubcopilot.com/mcp/`・OAuth）**を利用します。Docker や Personal Access Token（PAT）は不要です（[ADR-010](./docs/adr/010-official-remote-github-mcp.md)）。

#### GitHub MCP の認証（OAuth）

`mcp.json` には URL のみが書かれており（トークンは含まれない）、`setup.sh` 実行後に Claude Code 内で OAuth 認証します。

```
/mcp        # GitHub を選び、ブラウザで OAuth 認証する
```

トークンは Claude Code が安全に保管するため、dotfiles にも環境変数にもシークレットは残りません。

> **既存マシン（旧 Docker 方式から移行する場合）**: `install.py` の MCP マージは「不足分のみ追加」なので、`~/.claude.json` に残る旧 `GitHub`（docker）エントリは自動では置き換わりません。`claude mcp remove GitHub` で旧定義を消してから `./setup.sh` を再実行する（または `~/.claude.json` の該当エントリを手動で書き換える）と新方式に切り替わります。不要になった Keychain の `github-pat` と `~/.zprofile` の `GITHUB_PERSONAL_ACCESS_TOKEN` も削除して構いません。

### インストール

```bash
git clone https://github.com/ShigetomoYamamoto/claude-config.git ~/dotfiles/claude-config
cd ~/dotfiles/claude-config
./setup.sh
```

`setup.sh` は実体は `install.py` を呼ぶ薄いラッパーです（JSON マージと symlink は bash に不向きなため）。`python3 install.py` を直接実行しても同じです。`--dry-run` を付けると**何も書き込まずに**変更内容だけ表示します。

```bash
./setup.sh --dry-run   # 変更計画を確認（書き込みなし）
./setup.sh             # 適用
```

以下を行います：

1. **preflight check** — 必須ツール（python3・git）の確認
2. `agents/`, `commands/`, `hooks/`, `rules/`, `skills/`, `workflows/` を `~/.claude/` に **シンボリックリンク**（repo を編集すれば即 live に反映。実体ディレクトリがあれば `~/.claude/.backup/` に退避してからリンク化）
3. `settings.json` を **構造マージ**（下記）。`settings.json.template` のパスを解決して反映するが、**既存の設定は決して破壊しない**
4. `mcp.json` の MCP サーバー設定を `~/.claude.json` にマージ（既存は保持、不足分のみ追加）

書き込み前に置換対象を `~/.claude/.backup/<timestamp>/` にバックアップします。

#### settings.json の構造マージ規則

`~/.claude/settings.json` は repo 管理の配線と、Claude が実行時に書き込む個人設定（`/effort`・`/model`・通知音など）が同居するため、丸ごと上書きすると個人設定が消えます（過去に通知設定が消えた原因）。そこでキー単位で、次の **2規則** だけでマージします：

- **FORCE（repo が勝つ＝更新が伝播）**：`hooks.PreToolUse` / `hooks.PostToolUse`（blocker 群）、`permissions.allow`（和集合）、`env`、`enabledPlugins`、`extraKnownMarketplaces`。template の値が live に反映される（配線を消したい場合は template 側を空にする。template が無言なら live はそのまま）
- **DEFAULT（live に無い時だけ template から補う。live に値があれば常に live が勝つ＝通知が残る理由）**：上記以外（`hooks.Stop` / `PermissionRequest` / `Notification`、`model`、`effortLevel` など）
- live に存在するキーは決して削除しない。書き込み前に必ずバックアップ

各ステップは `[1/4] ✓ ...` 形式で進捗表示します。失敗時はどのステップまで成功したかを表示します。

## 開発フロー

目的を渡すと `/autorun` が `rules/autorun-flow.md` の遷移に従い、**関門4点（要件確定・設計確定・PR作成・デプロイ）以外を自動連結**して自走します。全自動／サポートの2モードは、起点とゴールの違いだけ（同じ自走エンジンのパラメータ違い）です。

### 全自動モード（自由形式の目標 → デプロイ）

```
要件 →🚦 設計 →🚦 計画 → 実装(TDD) → 検証 → コミット → PR →🚦 (migrate) → デプロイ →🚦
🚦＝関門（人間が確認）。それ以外は自動連結。コミットは起動時の包括承認で自動。
```

**起動方法**
- `/autorun ユーザーのパスワードリセット機能を作って` — 目的を渡して自走
- `ユーザーのパスワードリセット機能を作って` — 日本語の要望でも可（要件フェーズから）

### サポートモード（具体タスク・Issue → PR）

```
タスク分析 → 計画 → 実装(TDD) → 検証 → コミット → PR →🚦
```

**起動方法**
- `/autorun Issue #12 を実装して` — Issue を渡して自走
- `ログイン時のエラーが表示されないバグを直して` — 具体タスクでも可

> **関門でのみ止まります**（全自動＝要件・設計・PR・デプロイ／サポート＝PR）。それ以外は自動連結。
> 各フェーズコマンド（`/requirements`・`/design`・`/plan`・`/commit`・`/create-pr` 等）は**単発でも使え**、その場合は従来どおりコマンド完了で停止して次を案内します（自動連結は autorun 文脈でのみ）。
> コード1実装だけを検証付きで回したいときは `loop-engineering` スキル（「〜を実装して」で起動）。

## 使い方

### パターン1: 既存プロジェクトへの導入

仕様書・設計書など必要な資料が揃っている前提です。

**ステップ1: AI エージェント自走基盤を生成**

```
/init-autonomous
```

スタックを自動検出し、以下を一括生成します：

- `.claude/settings.json` — スタック固有コマンドの権限設定（npm/pest/pytest/go/cargo など）
- `.claude/hooks/` — スタック別デバッグ出力検知（JS/TS の `console.log`・Python の `print()` など）
- `CLAUDE.md` — プロジェクトルール・エンティティ・ロール定義
- `.claude/rules/`, `.claude/commands/`, `.claude/agents/` — スタック固有の設定
- `docs/` — 仕様書テンプレート・ADR・コードマップ
- `.github/` — CI/CD・PR テンプレート・Issue テンプレート

**ステップ2: 既存資料を Claude に読み込ませる**

`/init-autonomous` の実行中に「既存の仕様書・設計書はありますか？」と聞かれます。ファイルパスを答えると Claude が内容を読み取り、`CLAUDE.md` の参照パスを自動で更新します。

以降は通常の開発フローで進めます。

---

### パターン2: 新規プロジェクト作成直後

コードも資料もほぼない状態から始めます。まず要件定義・設計を行い、その成果物を使って自走基盤を構築します。

```
# ステップ1: 要件定義
/requirements

# ステップ2: システム設計
/design

# ステップ3: AI エージェント自走基盤を生成
/init-autonomous
```

機能要件・非機能要件・データモデル・API コントラクトを定義します。承認するまで実装には進みません。

```
# ステップ4: 設計内容を docs/ に反映
docs/01_product-specifications.md  ← /requirements + /design の成果物
docs/02_detailed-design.md         ← /design の詳細設計
```

```
# ステップ5: 実装開始（/autorun で自走、または個別コマンド）
/autorun <目的>   # 関門4点(要件・設計・PR・デプロイ)以外を自動連結して自走
# または個別に: /plan → /tdd → /commit → /create-pr → /migrate → /deploy
```

---

## 別マシンで最新の設定を取得するとき

`agents/`・`commands/`・`rules/`・`skills/`・`hooks/`・`workflows/` は symlink なので **`git pull` だけで即反映**されます。`settings.json.template` や `mcp.json` を変更したときだけ `./setup.sh` を再実行してください。

```bash
cd ~/dotfiles/claude-config
git pull
./setup.sh   # settings.json.template / mcp.json を変えたときのみ必要
```

## MCP・プラグインの管理

| 種別 | 管理方法 |
|---|---|
| MCP サーバー（GitHub / Playwright / Figma） | `mcp.json` → `setup.sh` が `~/.claude.json` にマージ |
| プラグイン（Slack） | `settings.json.template` の `enabledPlugins` で自動有効化 |

新しい MCP サーバーを追加した場合は `mcp.json` に追記して `setup.sh` を再実行してください。  
新しいプラグインを有効化した場合は `settings.json.template` の `enabledPlugins` に追記してください。

## 拡張方法

新しいエージェント・コマンド・hook・workflow・MCP を追加する手順です。`agents/`・`commands/`・`rules/`・`skills/`・`hooks/`・`workflows/` は symlink のため、追加後は他マシンで `git pull` するだけで反映されます（`settings.json.template` や `mcp.json` を変えた場合のみ `setup.sh` を再実行）。

### 新エージェントを追加

1. `agents/<name>.md` を作成（YAML フロントマター + 英語の人格定義・300 行以内）
2. 必要なら `commands/<name>.md` を作成（日本語の薄いラッパー）
3. `rules/agents.md` のトリガー表に追記（自動起動が必要な場合）

### 新コマンドを追加

1. `commands/<name>.md` を作成（YAML フロントマター + 日本語・500 行以内）
2. 必要なら対応するエージェントを `agents/<name>.md` に作成
3. README の「使い方」セクションに記載

### 新 hook を追加

1. `hooks/<name>.py` を作成（100 行以下・単一責務）
2. `settings.json.template` の `hooks` セクションに配線追加

設計原則：

- 予期せぬエラーは `exit 0`（Claude を止めない）
- 意図的ブロックのみ `exit 2`
- ネットワーク通信禁止（ローカル処理のみ）

### 新 workflow を追加

1. `workflows/<name>.js` を作成（Workflow ツールで起動できる JS。`meta` 必須、mode 分岐・引数バリデーションを持たせる）
2. 起動元のスキル / コマンド（例: `skills/loop-engineering/SKILL.md`）から参照を追記
3. コミット → 他マシンで `git pull`（`workflows/` は symlink なので即反映。settings 側の配線追加は不要）

### 新 MCP を追加

1. `mcp.json` の `mcpServers` に追記
2. README の前提条件セクションに必要なツールを追記
