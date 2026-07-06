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
| `agents/` | 16体のカスタムエージェント（architect, planner, tdd-guide, reviewer, fixer, requirements-analyst, deploy-runner など）。コードレビューは公式 `pr-review-toolkit` に委譲（[ADR-012](./docs/adr/012-official-plugins-for-git-review-security.md)） |
| `commands/` | 23個のスラッシュコマンド（/requirements, /design, /plan, /tdd, /create-pr, /deploy, /autorun, /review-loop, /verify-loop など）。コミット/ブランチ掃除は公式 `commit-commands` に委譲 |
| `hooks/` | 品質ガード・安全装置（シークレット検出・秘匿ファイルのステージ防止・doc 生成ブロック・保護ブランチ編集ガード・git 破壊操作ブロック・PR base チェック・大量削除確認） |
| `rules/` | コーディングスタイル・テスト・セキュリティ・エージェント運用ルール・Claude 使用効率化・自走/並列/メモリのループ運用ルール |
| `skills/` | 参照スキル（loop-engineering, 3-line-contract, git-workflow）。TDD は `rules/testing.md`＋`/tdd`、セキュリティは公式 `security-guidance`＋`rules/security.md` に集約 |
| `workflows/` | オーケストレーション用 Workflow テンプレート（loop-engineering-large-A: 大規模Aの計画→赤確認→実装→検証） |
| `templates/` | コマンドが生成するファイルのテンプレート集（`init-autonomous/`: `/init-autonomous` が出力する CLAUDE.md/rules/commands/agents/docs/.github 等。肥大化したコマンド本体から外出し） |
| `docs/` | 要件定義・アーキテクチャ・ADR |
| `settings.json.template` | Claude Code 設定テンプレート（パス自動解決・プラグイン有効化を含む。構造マージのベース） |
| `mcp.json` | MCP サーバー設定（GitHub / Playwright / Figma） |
| `install.py` | インストーラ本体（静的ディレクトリの symlink 化・settings.json の構造マージ・mcp マージ。`--dry-run` 対応） |
| `setup.sh` | `install.py` を呼ぶ薄いラッパー（後方互換用） |

## ループ自走（Loop Engineering）運用

目的を渡せば検証しながら自走する仕組みを、安全装置（`rules/loop-safety.md`）を核に、5層で備えています。規律としての定義（4不変条件・再帰モデル・入口一元化・ゲート導出）は [ADR-014](./docs/adr/014-loop-engineering-as-discipline.md) が正本です。

| 層 | 主な成果物 | 役割 |
|----|-----------|------|
| **ミクロ実装** | `skills/loop-engineering/`・`commands/review-loop`（+`reviewer`/`fixer`）・`workflows/loop-engineering-large-A.js` | 1タスクを VISION→テスト→レッド/グリーン→レビュー往復→完了判定で完成させる（強さ A/B/C を自動選択） |
| **マクロ自走** | `docs/autorun-flow`（遷移定義）・`commands/autorun`（解釈）・`docs/adr/007`・`008` | 要件→設計→実装→PR/デプロイを、関門4点（要件・設計・PR・デプロイ）以外を autorun-flow の遷移表に従い自動連結 |
| **安全（横串）** | `rules/loop-safety.md` | 前提条件・ハードストップ・ゴールドリフト・不可逆操作確認（全層が参照する正本） |
| **メモリ（横串）** | `rules/memory.md` | セッションを跨ぐ学習を `memory/` に書き戻す（アウターループ） |
| **並列（横串）** | `rules/parallel-worktree.md` | 並列エージェントが書き込み競合する場合の worktree 分離 |

**安全の原則:** ブレーキ（ハードストップ・専用ブランチ・機械的な成功判定）を先に設定してから自走させる。機械的に成功判定できないタスクは自走させない。

**使い方の手順は下記「開発の進め方（規模別）」を参照。** レビュー→修正の自動往復は `/review-loop`（通常）、または `/verify-loop`（反証検証つきの手動変種・セキュリティ重点。自走の verify ゲートは `/review-loop`）。

## settings.json.template の主な設定

- `defaultMode: auto` — ほとんどの操作を自動承認
- `Bash(git *)` / `Bash(gh *)` — どのプロジェクトでも git/gh 操作が確認なしで動作
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: 1` — 複数エージェントの並列実行を有効化
- `enabledPlugins` — Slack・`github`・`commit-commands`・`pr-review-toolkit`・`security-guidance`・`frontend-design` プラグインを自動有効化（[ADR-012](./docs/adr/012-official-plugins-for-git-review-security.md)・[ADR-019](./docs/adr/019-settings-template-scope.md)）
- フック: PreToolUse（保護ブランチ編集ガード・doc 生成ブロック・秘匿ファイルのステージ防止・git 破壊操作ブロック・PR base チェック・大量削除確認・コミットメッセージ規約チェック）、PostToolUse（シークレット検出）

## 新しいマシンへのインストール

### 前提条件

| ツール | 最低バージョン | 備考 |
|---|---|---|
| python3 | 3.8+ | `install.py`（インストーラ本体）と hook 用 |
| bash | 3.2+ | `setup.sh` ラッパー用（`python3 install.py` を直接呼べば不要） |
| git | 2.0+ | |

対応 OS: macOS / Linux（Windows 非対応）

> GitHub MCP は**公式 `github` プラグイン**を利用します（`mcp.json` では管理しません）。プラグインはリモートサーバー（`https://api.githubcopilot.com/mcp/`）へ `Authorization: Bearer ${GITHUB_PERSONAL_ACCESS_TOKEN}` で接続するため、**PAT が必要**です。Docker は不要です（[ADR-011](./docs/adr/011-official-github-plugin.md)）。

> **なぜ OAuth ではないのか**: 公式リモートサーバーへ OAuth 直結も試みましたが、GitHub の認可サーバーは動的クライアント登録（DCR / RFC 7591）に非対応で、Claude Code は `Incompatible auth server: does not support dynamic client registration` で接続に失敗します。公式プラグインが採る PAT ヘッダ方式が現実的な唯一の経路です（経緯は [ADR-010](./docs/adr/010-official-remote-github-mcp.md) → [ADR-011](./docs/adr/011-official-github-plugin.md)）。

#### GitHub MCP のセットアップ

**1. PAT を Keychain / Keyring に保管し、env 変数へ展開する**（[ADR-005](./docs/adr/005-keychain-pat.md)。dotfiles にトークンを残さないため）

```bash
# macOS
security add-generic-password -a "$USER" -s "github-pat" -w "ghp_xxxx"
# ~/.zprofile に追記
export GITHUB_PERSONAL_ACCESS_TOKEN="$(security find-generic-password -a "$USER" -s "github-pat" -w)"

# Linux（GUI 環境前提）
secret-tool store --label="github-pat" service github-pat
# ~/.zprofile に追記
export GITHUB_PERSONAL_ACCESS_TOKEN="$(secret-tool lookup service github-pat)"
```

Fine-grained PAT を使い、最小スコープ・30〜90 日のローテーションで運用します。

**2. 公式プラグインを導入する**（Claude Code 内）

```
/plugin     # claude-plugins-official マーケットプレイスから `github` を導入
```

プラグインの `.mcp.json` が `${GITHUB_PERSONAL_ACCESS_TOKEN}` を読むため、env 変数を設定済みなら追加設定は不要です。

> **既存マシンからの移行**: `~/.claude.json` に旧 `GitHub`（http・認証ヘッダなし）エントリが残っていると壊れたまま重複します。`claude mcp remove GitHub` で除去してください（GitHub MCP はプラグイン側の `github` が担います）。

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
2. `agents/`, `commands/`, `hooks/`, `rules/`, `skills/`, `workflows/`, `templates/` を `~/.claude/` に **シンボリックリンク**（repo を編集すれば即 live に反映。実体ディレクトリがあれば `~/.claude/.backup/` に退避してからリンク化）
3. `settings.json` を **構造マージ**（下記）。`settings.json.template` のパスを解決して反映するが、**既存の設定は決して破壊しない**
4. `mcp.json` の MCP サーバー設定を `~/.claude.json` にマージ（既存は保持、不足分のみ追加）

書き込み前に置換対象を `~/.claude/.backup/<timestamp>/` にバックアップします。

#### settings.json の構造マージ規則

`~/.claude/settings.json` は repo 管理の配線と、Claude が実行時に書き込む個人設定（`/effort`・`/model`・通知音など）が同居するため、丸ごと上書きすると個人設定が消えます（過去に通知設定が消えた原因）。そこでキー単位で、次の **2規則** だけでマージします：

- **FORCE（repo が勝つ＝更新が伝播）**：`hooks.PreToolUse` / `hooks.PostToolUse`（blocker 群）、`permissions.allow`（和集合）、`env`、`enabledPlugins`、`extraKnownMarketplaces`。template の値が live に反映される（配線を消したい場合は template 側を空にする。template が無言なら live はそのまま）
- **DEFAULT（live に無い時だけ template から補う。live に値があれば常に live が勝つ＝通知が残る理由）**：上記以外（`hooks.Stop` / `PermissionRequest` / `Notification`、`model`、`effortLevel` など）
- live に存在するキーは決して削除しない。書き込み前に必ずバックアップ

各ステップは `[1/4] ✓ ...` 形式で進捗表示します。失敗時はどのステップまで成功したかを表示します。

## 開発の進め方（規模別）

`/autorun` が `docs/autorun-flow.md` の遷移に従い、**関門4点（要件・設計・PR・デプロイ）以外を自動連結**して自走します。タスクの規模で入口と通る段が変わります。

### 入口は3つ

| 入口 | 何をする |
|---|---|
| 「〜作って／直して」 | `loop-engineering` スキル。STEP0 で規模判定 → 小さければそのまま実装、要件・設計や多段出荷が要れば `/autorun` に自動格上げ |
| `/autorun <目的>` | 入力の形でモード自動判定。**自由形式の目標→全自動**（ゴール=デプロイ）／**具体タスク・Issue→サポート**（ゴール=PR） |
| 各フェーズ単発 | `/requirements` `/design` `/plan` `/tdd` `/create-pr` `/migrate` `/deploy` `/review-loop` 等。1段ずつ手動、コマンド完了で停止 |

迷ったら自然言語で頼めばよい（loop-engineering が必要に応じて `/autorun` へ上げる）。最初からパイプラインを回すなら明示的に `/autorun`。

### 全規模に共通の前提（仕組みが強制する）

1. **専用ブランチで動く** — main/master/develop 上は編集が hook でブロックされる。`/autorun` は protected なら起動時に `/create-branch` する。
2. **実装・検証の自動段は機械検証が前提** — `/autorun` は起動時に test/lint/typecheck が実行可能かを確認し、**無ければ早期停止して不足を報告**する（→ 新規プロダクトは先に基盤整備＝下記④）。
3. **人間が止まるのは関門4点＋不可逆操作だけ** — commit は起動時の一度きりの包括承認で自動。

### ① 1ファイル級の変更（typo・小修正・既存設計内の小機能）

普通に「〜を直して／実装して」と頼む（`/autorun` 不要）。`loop-engineering` が STEP0 で **C（そのまま）／B（ミニ）／A（フル: VISION→テスト→赤緑→`/review-loop`→完了判定）** を自動選択。大きいと判明したら自分で `/autorun` に格上げ。

### ② 既存プロジェクトの定義済みタスク／Issue／バグ（サポート）

```
/autorun Issue #12 を実装して
/autorun ログイン時にエラーが表示されないバグを直して
```

`タスク分析 → 計画 → 実装(TDD) → 検証 → コミット → PR🚦`（🚦＝関門）。止まるのは **PR** だけ、ゴール=PR（デプロイはしない）。前提: そのリポジトリに test/lint があること（無ければ下記④の `/init-autonomous`）。

### ③ 既存プロジェクトの新機能（要件・設計が要る／全自動）

```
/autorun パスワードリセット機能を作って
```

`要件🚦 → 設計🚦 → 計画 → 実装(TDD) → 検証 → コミット → PR🚦 → migrate → デプロイ🚦`。**設計**は新DBスキーマ／新API／技術選定／境界変更がどれも不要なら自動スキップ。デプロイ不要なら②（サポート）で回す。

### 関門を極小化して一気通貫で流す（`--vibing`）

```
/autorun --vibing パスワードリセット機能を作って
/autorun --vibing Issue #12 を実装して
```

`--vibing` は②③に重畳する**直交フラグ**（第3モードではない・[ADR-015](./docs/adr/015-vibing-mode.md)）。モード（full-auto / support）は無印 `/autorun` と同じく**入力で自動判定**される（上の例なら「機能を作って」→ full-auto でデプロイまで、「Issue #12」→ support で PR まで）。**実行の不可逆操作の事前確認だけを外し、アーキ方向判断は人間が握る**という配分で、`PR🚦 → 本番デプロイ🚦` を無確認の自動連結に降格する:

`要件🚦 → 設計🚦(条件付) → 計画 → 実装(TDD) → 検証 → コミット → PR(→main直結) → migrate → デプロイ`

- **残る人間ゲートは2系統だけ**: ①方向ゲート（**要件**は常時、**設計**は新DB/新API/技術選定/境界変更が要るときのみ）②**巻き戻し不能な操作**（外部送信・破壊的 migrate(DROP/RENAME)・auto-rollback 不能なデプロイ）。検出は機械述語で、判定不能なら止める（fail-safe=gate）。
- **外す安全弁は invariant 4（不可逆の事前確認）の一部のみ**。ハードストップ・maker≠checker・機械的な完了判定（invariant 1/2/3）は維持。代償として不可逆操作は事後監査＋auto-rollback＋transcript 記録を残す。
- **残存リスク（理解して使う）**: PR push と巻き戻し可能なデプロイの事前ガードが規範からも物理層からも消える。誤実行は事後にしか気づけない。巻き戻し不能操作だけは上記のとおりゲートを残す。
- PR→main 直結は `pr-base-checker.py` の末尾コメントマーカーで通す（無印 `/autorun` は従来どおり develop ベース・関門4点で不変）。

## 新規プロダクトの立ち上げ・基盤整備（/init-autonomous）

### ④ 1からプロダクトを作る（新規・greenfield）

空リポジトリは test/lint が無く、③をそのまま流すと前提2で早期停止します。**「先に基盤、後に自走」**の順で進めます:

```
1. /requirements → /design   # 要件・設計を固める（技術選定もここ。機械検証不要の人間ゲート）
2. /init-autonomous          # スタック検出 → test/lint/typecheck・hooks・CLAUDE.md・docs・.github を生成
                             #   実行中に既存の仕様書/設計書のパスを聞かれる → 取り込む
3. /autorun <機能>           # 以降は機能・マイルストーン単位で自走（1コマンドで全部ではない）
```

`/init-autonomous` が生成するもの: `.claude/settings.json`（スタック別コマンド権限）・`.claude/hooks/`（スタック別デバッグ出力検知）・`CLAUDE.md`（ルール/エンティティ/ロール）・`docs/`（仕様・ADR・コードマップ雛形）・`.github/`（CI・PR/Issue テンプレ）。

### 既存プロジェクトに後から基盤を入れる

仕様書・設計書が揃っているなら `1.` を飛ばして **`/init-autonomous` から**。実行中に既存資料のパスを答えると `CLAUDE.md` の参照を自動更新する。以降は②③で進める。

### 補足

- **手動で1段ずつ**回したいときは各フェーズコマンドを単発で（自動連結は `/autorun` 文脈のときだけ作動）。
- **ロールバックは自走に含まれない** — 自走は deploy 失敗時の*自動*ロールバックのみ。*手動*は `/rollback`。
- push／PR／デプロイ／破壊的マイグレーションは関門 or 確認で必ず止まる（push/PR を `gh` 経由にすると develop ベース強制等の物理層 hook も効く）。

---

## 別マシンで最新の設定を取得するとき

`agents/`・`commands/`・`rules/`・`skills/`・`hooks/`・`workflows/`・`templates/` は symlink なので **`git pull` だけで即反映**されます。`settings.json.template` や `mcp.json` を変更したとき、または **symlink 対象ディレクトリを新規追加したとき**（例: `templates/`）だけ `./setup.sh` を再実行してください。

```bash
cd ~/dotfiles/claude-config
git pull
./setup.sh   # settings.json.template / mcp.json を変えたときのみ必要
```

## MCP・プラグインの管理

| 種別 | 管理方法 |
|---|---|
| MCP サーバー（GitHub / Playwright / Figma） | `mcp.json` → `setup.sh` が `~/.claude.json` にマージ |
| プラグイン（Slack / github / commit-commands / pr-review-toolkit / security-guidance / frontend-design） | `settings.json.template` の `enabledPlugins` で有効化。本体は各マシンで `/plugin` から導入 |

新しい MCP サーバーを追加した場合は `mcp.json` に追記して `setup.sh` を再実行してください。  
新しいプラグインを有効化した場合は `settings.json.template` の `enabledPlugins` に追記してください。

> **公式プラグインの導入（各マシンで1回）**: `enabledPlugins` は有効化フラグで、本体は別途導入が必要です。Claude Code 内で `/plugin` を開き、`claude-plugins-official` から `commit-commands`・`pr-review-toolkit`・`security-guidance`・`github`・`frontend-design`（と `slack`）を導入してください。git/レビュー/セキュリティを公式へ寄せた背景は [ADR-012](./docs/adr/012-official-plugins-for-git-review-security.md)。コミット規約・develop ベース PR・保護ブランチ保護などの安全保証は hooks 側が担保するため、薄い公式コマンドでも規律は保たれます。

## 拡張方法

新しいエージェント・コマンド・hook・workflow・MCP を追加する手順です。`agents/`・`commands/`・`rules/`・`skills/`・`hooks/`・`workflows/`・`templates/` は symlink のため、追加後は他マシンで `git pull` するだけで反映されます（`settings.json.template` や `mcp.json` を変えた場合のみ `setup.sh` を再実行）。

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
