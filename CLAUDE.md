# CLAUDE.md — claude-core リポジトリでの作業ルール

このリポジトリは `~/.claude` へ copy インストールされる **claude-core（ドメイン中立）の正本**
（[ADR-023](./docs/adr/023-three-foundation-split.md)）。単一設定を core / engineering /
work-agent の3 foundation に分割済みで、`~/.claude` へは **copy 型インストーラ**
（`installer.py` + `install.py`）で導入する（symlink は廃止）。通常のプロジェクトと異なる制約がある。

## 作業フロー（最重要）

- **primary clone（通常のクローン場所）は通常 `main` に留める。** 実機 `~/.claude` へは `install.py` が `rules/` `hooks/` `skills/` を **copy**（symlink ではない）するため、live 反映には再インストールが要る（ADR-023）。この repo が正本である以上、意図せぬ規律逸脱を避ける目的で「今 primary が何を指しているか」を常に把握できる状態を維持する（＝下記 trial install 中を除き `main`）。
- 編集は **develop 起点の git worktree** で行う: `git worktree add ../wt-<task> -b <prefix>/<summary>_YYYYMMDD origin/develop` → PR（base=develop）→ merge 後に primary で `git pull`。セッションごと worktree に入る場合は EnterWorktree を使う。**この repo（claude-core）自体は保護ブランチ編集ガード等の git hook を同梱しない**（`protected-branch-edit-guard.py` / `pr-base-checker.py` は claude-engineering 側。ADR-023 / `docs/migration/inventory.md`）。ブランチ規律は開発者の実機側 hooks か手動運用に依存する。
- **hook 導入前の古いブランチを primary clone で checkout しない。** 実機 `~/.claude/hooks/` を古い内容で copy 上書きすると、settings.json の配線は残る一方 hook 実体が壊れ **全 Bash がブロックされ得る**。誤って壊した場合は該当パスに `sys.exit(0)` だけのスタブを置いて復旧する。

### trial install — develop→main 昇格前に実機で試す

`installer.py` は primary clone が **今チェックアウトしているブランチの中身をそのままコピーする**だけで、`main` であることをコード上は要求しない（`git rev-parse HEAD` を manifest に記録するのみ）。「develop→main 昇格を経ないと実機で試せない」わけではないので、次の順で試してから決めてよい:

1. `git checkout develop && git pull` — primary を一時的に develop にする。
2. `python3 install.py update --dry-run` で差分確認 → 問題なければ `python3 install.py update` を適用（実機 `~/.claude` に develop の内容が反映される）。
3. **良ければ**: develop→main の昇格 PR を作り merge → primary を `git checkout main && git pull` → `python3 install.py update` で「正式版」として再適用（内容は同じだが manifest の revision が main の commit を指すようになる）。
4. **イマイチだったら**: `git checkout main && git pull` → `python3 install.py update` で実機を main の内容に戻すだけ（develop 側の変更は main に一切触れていないため、単純な巻き戻し）。

**primary が develop な状態は trial 専用の一時状態。** 昇格 or 差し戻しのどちらかで必ず `main` に戻す。「今どっちを指しているか分からない」まま放置しない。

## その他の前提

- ブランチ・コミット・PR の規約（develop 起点・PR base develop 固定など）はこの repo が own せず、claude-engineering foundation 側の hooks／rules が担保する。core にはこの種の git-workflow hook は無い。
- `rules/` `hooks/` `skills/` の構成や `settings-fragment.json` を変更したら、対象マシンで `python3 install.py`（update）の再実行が必要（ADR-023）。旧 `setup.sh` / `mcp.json` / `settings.json.template` は retired。
- `rules/*.md` は**毎セッション全文が常時ロード**される（サブディレクトリも再帰的に対象）。行数＝恒常的なコンテキストコストなので、追記時は密度を吟味する（オンデマンドで足りる内容は skill / docs へ。ADR-022 参照）。
- 大きな意思決定は `docs/adr/` に記録する（1決定1ファイル。既存 ADR 本文は改変せず、supersede か注記追記で扱う）。
