# claude-config 要件定義

## 1. 上位目的（要望）

人間の開発業務を Claude Code が肩代わり・サポートする。

### 2つのモード

| モード | 内容 |
|---|---|
| 全自動 | 要件を伝えたら設計・実装・テスト・コミット・PR・デプロイまで完了 |
| サポート | タスクや課題を渡したら PR まで Claude が進める |

### 人間が関与するポイント

| フェーズ | 関与度 |
|---|---|
| 設計（DB・API） | Claude が作成 → 人が確認・承認 |
| 実装・テスト | 全自動 |
| コミット・PR | 全自動 |
| デプロイ | 全自動 |

### このリポジトリの位置づけ

上記 2 モードを実現するための「土台・基盤」。

---

## 2. 機能要件

### A. 開発フローの提供

スタックに依存しない汎用的なフロー・ベース設定・テンプレートをグローバルに提供する。スタック固有の実装（デプロイ先・ビルドコマンドなど）はプロジェクト側に置く。

| ステップ | コマンド | エージェント |
|---|---|---|
| 要件分析 | `/requirements` | requirements-analyst |
| 設計 | `/design` | architect |
| 計画 | `/plan` | planner |
| 実装（TDD） | `/tdd` | tdd-guide |
| ビルド修正 | `/build-fix` | build-error-resolver |
| リファクタ | `/refactor-clean` | refactor-cleaner |
| テスト補完 | `/test-coverage` | tdd-guide |
| E2E | `/e2e` | e2e-runner |
| レビュー | `/code-review` | code-reviewer |
| セキュリティレビュー | （自動起動） | security-reviewer |
| コミット | `/commit` | — |
| PR作成 | `/create-pr` | — |
| マイグレーション | `/migrate` | migration-runner |
| デプロイ（検証・自動ロールバック込み） | `/deploy` | deploy-runner |
| 手動ロールバック | `/rollback` | rollback-runner |
| タスク分析 | `/analyze-task` | task-analyst |
| PR レビュー対応 | `/respond-review` | review-responder |
| ドキュメント更新 | `/update-docs` | doc-updater |
| コードマップ更新 | `/update-codemaps` | doc-updater |

#### 保留（将来追加候補）

| 項目 | 着手条件 |
|---|---|
| リリースノート / CHANGELOG 生成 | チーム化時（Issue #2） |
| 依存関係更新 | 既存ツールでカバーできない要求が出たとき（Issue #3） |
| 環境変数管理 | 複数プロジェクトで共通パターンが見えたとき（Issue #4） |

### B. 品質ガード

| 項目 | 配置 |
|---|---|
| テストカバレッジ 80% 以上の強制 | グローバル（`rules/testing.md`） |
| TDD 強制 | グローバル（`/tdd` + tdd-guide） |
| コードレビュー | グローバル（`/code-review` + code-reviewer） |
| セキュリティレビュー | グローバル（security-reviewer） |
| コーディングスタイル | グローバル（`rules/coding-style.md`・言語非依存に修正） |
| Claude 使用効率化 | グローバル（`rules/performance.md` → リネーム予定） |
| ビルド・型エラー修正 | グローバル（`/build-fix` + build-error-resolver） |
| デッドコード削除 | グローバル（`/refactor-clean` + refactor-cleaner） |
| アクセシビリティチェック | プロジェクト側 |
| パフォーマンス測定 | プロジェクト側 |
| 依存ライブラリ脆弱性チェック | Dependabot/Snyk に任せる（実装しない） |

### C. 安全装置

| 項目 | 配置 |
|---|---|
| シークレット検出 | グローバル hook（`secret-detection.py`）+ `/commit` 内で再チェック |
| 不要ドキュメント生成のブロック | グローバル hook（`doc-blocker.py`） |
| git 破壊的操作の防止 | グローバル hook（新規・`git push --force` / `reset --hard` / `clean -fd`） |
| 大量ファイル削除確認 | グローバル hook（新規） |
| PR の base ブランチチェック | グローバル hook（新規・base が `develop` 以外でブロック） |
| デバッグ出力検知（言語別） | プロジェクト側（`/init-autonomous` がスタック検出時に生成） |
| シークレットファイル誤コミット防止 | `.gitignore` で対応（追加実装不要） |
| 本番 DB 直接操作の防止 | プロジェクト側 |

### D. プロジェクト初期化

| 項目 | 提供形式 |
|---|---|
| プロジェクト基盤生成 | `/init-autonomous` |
| スタック自動検出 | `/init-autonomous` 内 |
| 既存資料の取り込み | `/init-autonomous` 内 |
| プロジェクト側 hook 生成 | `/init-autonomous` がスタック検出時にデバッグ出力検知を生成 |
| 再初期化コマンド | 実装しない（手動退避 + 再実行で対応） |
| プロジェクト整合性チェック | 実装しない（YAGNI） |
| onboarding ドキュメント生成 | 実装しない |

`/init-autonomous` 本体の見直し（テンプレート外出し・新要件対応）は Issue #1 で対応。

### E. マルチマシン同期

| 項目 | 内容 |
|---|---|
| 設定ディレクトリのコピー | `setup.sh`（`agents/` `commands/` `hooks/` `rules/` `skills/`） |
| Claude Code 設定生成 | `setup.sh`（`settings.json.template` → `~/.claude/settings.json`） |
| MCP 設定マージ | `setup.sh`（`mcp.json` → `~/.claude.json`、不足分のみ追加） |
| 事前検証（preflight check） | `setup.sh` に追加（必須ツールが無ければ案内して exit） |
| `settings.json` のバックアップ | 実装しない |
| dry-run モード | 実装しない |
| マシン固有設定 | 環境変数のみで管理（現状維持） |

---

## 3. 非機能要件

### 信頼性

| 項目 | 内容 |
|---|---|
| `setup.sh` 失敗時 | 即停止し、どのステップまで成功したかを表示 |
| `mcp.json` マージ | 不足分追加方式（既存設定を破壊しない） |
| hook の予期せぬエラー | exit 0 で Claude の動作を止めない |
| 意図的なブロック | `doc-blocker.py` のみ exit 2 |

### 移植性

| 項目 | 内容 |
|---|---|
| 対応 OS | macOS / Linux（Windows は対象外） |
| Linux | GUI 環境前提（`secret-tool` / libsecret 利用） |
| パス区切り文字 | フォワードスラッシュ前提 |
| 必須ツール最低バージョン | bash 3.2+ / Python 3.8+ / git 2.0+ / Docker 20.0+ |

### セキュリティ

| 項目 | 内容 |
|---|---|
| シークレット混入防止 | `.gitignore` + `secret-detection.py` hook + `/commit` 内で再チェック |
| GitHub PAT 管理 | macOS Keychain / Linux libsecret 経由 |
| PAT 運用ルール | Fine-grained PAT・有効期限 30〜90 日・最小スコープ |
| 禁止事項 | `.git/config` への直書き |
| hook の外部通信 | 禁止（ローカル処理のみ） |

#### macOS 手順

```bash
security add-generic-password -a "$USER" -s "github-pat" -w "ghp_xxxx"
# ~/.zprofile に追記
export GITHUB_PERSONAL_ACCESS_TOKEN="$(security find-generic-password -a "$USER" -s "github-pat" -w)"
```

#### Linux 手順

```bash
sudo apt install libsecret-tools  # または sudo dnf install libsecret
secret-tool store --label="github-pat" service github-pat
# ~/.zprofile に追記
export GITHUB_PERSONAL_ACCESS_TOKEN="$(secret-tool lookup service github-pat)"
```

### 保守性

| 項目 | 内容 |
|---|---|
| ファイルサイズ上限（commands） | 500 行 |
| ファイルサイズ上限（agents） | 300 行 |
| ファイルサイズ上限（rules） | 200 行 |
| ファイルサイズ上限（skills） | 300 行 |
| ファイルサイズ上限（hooks） | 100 行 |
| 1ファイル1責務 | 明文化 |
| 重複の禁止 | 同じ情報は1箇所に集約 |

### 拡張性

| 項目 | 内容 |
|---|---|
| 新エージェント・新コマンド・新 hook の追加手順 | README に明文化 |
| 既存の振る舞いを変えない | 新規追加は既存を壊さないこと |
| 5レイヤー構造を固定 | Behavior / Workforce / Guardrails / Wiring / Installer |

### 観測性

| 項目 | 内容 |
|---|---|
| `setup.sh` のログ | 現状維持 |
| hook の警告メッセージ | 現状維持 |
| Stop 通知音 | 現状維持 |

---

## 4. 受け入れ基準

形式的なテストシナリオは作らない。

| 項目 | 内容 |
|---|---|
| 検証方法 | 日々の運用で気づいた不足・違和感を GitHub Issue として記録 |
| 改善サイクル | Issue を起点に随時調整 |

---

## 5. 制約・前提条件

| 項目 | 内容 |
|---|---|
| 必須ツール | bash 3.2+ / Python 3.8+ / git 2.0+ / Docker 20.0+ |
| 対応 OS | macOS / Linux（GUI 環境前提・Windows 非対応） |
| Claude Code 規約 | `~/.claude/` ディレクトリ構造に準拠 |
| 日本語話者前提 | commands は日本語、コミットメッセージ description も日本語 |
| ユーザー数 | 個人利用（将来チーム化を想定） |
