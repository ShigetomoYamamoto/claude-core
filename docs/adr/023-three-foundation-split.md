# ADR-023: グローバル単一設定を3つの独立 foundation（core / engineering / work-agent）へ分割し、symlink を copy 型インストーラへ置換する

**ステータス**: proposed（staging 実装済み・リモート/live 適用は未承認）

**日付**: 2026-07-12

**関連して狭める/更新する**: ADR-001（2層構造）/ ADR-004（コピー型）/ ADR-009（symlink+settings マージ）/ ADR-019（settings テンプレのスコープ）/ ADR-022（docs を symlink 対象に追加）。**既存 ADR 本文は改変しない**。本 ADR が方式・置き場所・スコープを更新する。

## コンテキスト

現行 claude-config は「グローバル ~/.claude 単一・symlink 方式」で、内容が開発（engineering）に強く偏る（git/PR/worktree/TDD/エージェント群/開発 hook/広い git・gh 権限/開発プラグイン）。これらはスタック非依存というだけで常時ロードのグローバル core に居座り、(1) 開発と無関係なセッションにも常時コストを課し、(2) 将来の業務（work-agent）用途と混線する。symlink 方式は repo 移動でリンク切れし、live ~/.claude のユーザーファイルを消す事故歴があり（ADR-009）、単一正本が全マシン・全ドメインに直結するためドメイン分離ができない。

## 決定

単一設定を、ターゲットも所有も重ならない **3つの独立 foundation** に分割する。傘リポジトリ・親設定ディレクトリは作らない。

| foundation | インストール先 | 所有 |
|---|---|---|
| claude-core | ~/.claude のみ | ドメイン中立の振る舞い・安全ガード |
| claude-engineering | 明示指定した1プロジェクトの .claude/ | 開発ワークフロー一式 |
| claude-work-agent | 明示指定した1プロジェクトの .claude/ | 業務/運用ワークフロー |

- **symlink 廃止。** 各 foundation は自前の copy 型インストーラ（`installer.py` + `install.py`）を持ち、`<target>/.<pack>.manifest.json`（pack 名・source rev・管理ファイル+sha256・backup 位置）が所有境界。install/update/uninstall は manifest 内かつハッシュ一致のファイルのみ書換/削除し、未知ファイル・ローカル改変ファイルは触らない（--force 時のみ backup 後）。--dry-run・衝突検出・backup・冪等 update・境界チェックを備え、symlink は使わない。
- **1プロジェクト=1ドメイン。** engineering は work-agent 管理下のプロジェクトを拒否し、その逆も同様（相手の manifest 検出で refuse）。
- **core は最小・中立のみ。** 常時ロード rules は core に置くが「スタック非依存でも開発ワークフローなら core に残さない」。開発規範（coding-style/git-workflow/parallel-worktree/testing/agents/loop-safety、および security のコード観点）は engineering へ。core は answer-only/collaboration-style/claude-efficiency/memory/role-separation と、新設の中立カーネル `safety-irreversible`（不可逆操作は人間確認・ループの機械的完了条件と hard stop・maker≠checker）と `secret-hygiene`（秘密の基本衛生）のみ。
- **core はグローバル MCP を持たず、開発/業務プラグインをグローバル有効化しない。** MCP・資格情報・ワークスペース ID・スタック統合はプロジェクトローカル。work-agent は notion-crien / notion-shigetomo（別ワークスペースへの意図的2サーバ例外）と Google ルートを**資格情報なしの雛形**として保持する。Figma/GitHub/Playwright/Vercel/Supabase/Nx/Unity は必要なプロジェクトのみ、公式統合を優先。
- **settings.json は引き続きキー単位マージ**（Claude が実行時に書くため上書きせず・live キーを削除しない）。各 foundation は自分の hook 配線のみを持つ settings-fragment を持ち、`__TARGET__` を解決してマージ。live が壊れた JSON のときは触らず警告のみ（live 保護）。

## 移行と巻き戻し

- staging（`~/src-works/claude-foundations-staging/`）で3 repo を先行実装。core は現 repo の完全クローンで**履歴を保持**し、承認後にリモート/ローカルを claude-core にリネームする候補。engineering/work-agent は独立 repo（submodule でも core の入れ子でもない）。
- 移行手順（別途・人間承認の上で）: ① core を ~/.claude に copy インストール（現行 symlink を退避）→ ② 開発プロジェクトに engineering を `--project` 指定でインストール → ③ 業務プロジェクトに work-agent を `--project` 指定でインストール。各段階は独立で、失敗時は uninstall（manifest 境界）で戻せる。symlink 時代の install.py(旧)/setup.sh/mcp.json/settings.json.template は retired。
- 巻き戻し: 各 pack の uninstall は manifest 内・ハッシュ一致ファイルのみ削除し backup を残す。settings.json は uninstall で触らない（live 保護）。

## auto-memory の限界（誇張しない）

Claude Code のランタイム memory は Claude Code のプロジェクトパスに紐づく機能で、インストーラが完全分割できるものではない。ドメイン分離は「別プロジェクトルート＋定期監査」で運用的に担保する。pack が Claude Code 以上の隔離を強制できるとは主張しない。

## GitHub リポジトリ/Issue 移行（実行は保留）

core = 現 repo のリネーム候補（履歴・core 系 Issue を移動）。engineering/work-agent は新 repo。Issue は `docs/migration/issue-mapping.md` の対応表に従い、core に横断親 Issue を1つ立てて各 repo の実装 Issue をリンクする。リモート操作（repo 作成/リネーム/Issue 移送/作成/close）は本 ADR では一切実行しない。

## 結果

### Positive
- 常時ロード core が最小化し、開発コストが開発プロジェクトのみに局在。ドメイン混線を解消。
- copy 型 manifest 境界で live ユーザーファイル破壊事故（ADR-009 の負債）を構造的に排除。repo 移動でリンク切れしない。
- 1プロジェクト=1ドメインの相互排他で設定衝突を防止。

### Negative
- 3つのインストーラ・3つの README を保守（ただしターゲット非重複でドリフトリスクは低い）。
- engineering をプロジェクトに入れる一手間が増える（旧: グローバル1発）。
- work-agent は現状ほぼ空のスキャフォールド（業務ワークフローは今後定義）。

## 「最小の可逆選択」で決めた判断（本 ADR に記録）

1. loop-safety と security を分割し、中立カーネルのみ core（safety-irreversible / secret-hygiene）。残りは engineering。
2. opus-execution-guard + role-separation は core（モデルコスト/役割は中立ガード）。
3. 3-line-contract / memory-dream は core（中立のタスク整形・KB 保守）。
4. env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS / permissions.defaultMode は core、git/gh/curl 権限と開発プラグインは engineering、slack は work-agent。

いずれもファイル移動/フラグ移動のみで取り消し容易。

## 関連
- ADR-001 / ADR-004 / ADR-009 / ADR-019 / ADR-022（本 ADR が方式・置き場所・スコープを更新。本文は改変せず）
- 実装: 各 repo の `installer.py` / `install.py` / `settings-fragment.json` / `tests/`
- `docs/migration/inventory.md`（資産分類）・`docs/migration/issue-mapping.md`（Issue 対応）
