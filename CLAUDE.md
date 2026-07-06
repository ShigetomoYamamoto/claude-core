# CLAUDE.md — claude-config リポジトリでの作業ルール

このリポジトリは `~/.claude` に symlink される **live 設定の正本**（ADR-009）。通常のプロジェクトと異なる制約がある。

## 作業フロー（最重要）

- **primary clone（通常のクローン場所）は常に `main` に留める。** `~/.claude/{rules,hooks,skills,commands,...}` が symlink でここを参照しており、ブランチを動かすと全セッションの live 設定が変わる。
- 編集は **develop 起点の git worktree** で行う: `git worktree add ../wt-<task> -b <prefix>/<summary>_YYYYMMDD origin/develop` → PR（base=develop）→ merge 後に primary で `git pull`。セッションごと worktree に入る場合は EnterWorktree を使う（protected-branch-edit-guard はセッション CWD のブランチで判定するため、primary に居たまま worktree のファイルを編集しようとするとブロックされる）。
- **hook 導入前の古いブランチを primary clone で checkout しない。** `~/.claude/hooks/*.py` が symlink 経由で消える一方 settings.json の配線は残るため、**全 Bash がブロックされる**。誤って壊した場合は該当パスに `sys.exit(0)` だけのスタブを置いて復旧する。

## その他の前提

- ブランチ・コミット・PR の規約は `rules/git-workflow.md` と hooks が担保する（PR base は develop 固定・`pr-base-checker.py`）。
- `settings.json.template` / `mcp.json` / symlink 対象ディレクトリ構成（install.py）を変更したら各マシンで `./setup.sh` の再実行が必要（ADR-009 / ADR-019 / ADR-022）。静的ディレクトリ内のファイル変更は `git pull` だけで全マシンに反映される。
- `rules/*.md` は**毎セッション全文が常時ロード**される（サブディレクトリも再帰的に対象）。行数＝恒常的なコンテキストコストなので、追記時は密度を吟味する（オンデマンドで足りる内容は skill / docs へ。ADR-022 参照）。
- 大きな意思決定は `docs/adr/` に記録する（1決定1ファイル。既存 ADR 本文は改変せず、supersede か注記追記で扱う）。
