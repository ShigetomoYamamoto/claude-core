# ADR-036: 夜間モード中は、push・PR・外への書き込みを hook で止める

**ステータス**: accepted

**日付**: 2026-11-25

**関連**: Notion ID47（夜の作業規則）、[ADR-006](./006-hook-error-policy.md)（hook の例外処理）、[ADR-028](./028-command-string-guard-limits.md)（文字列ガードの限界）、[ADR-031](./031-hook-merge-by-ownership.md)（配線のマージ）

## コンテキスト

- 夜の AI 作業の規則は次のとおり。夜の作業は、他の人から見えないところで終わらせる。ローカルの作業ブランチまでにして、push・PR・外への書き込み（Slack・Gmail・Notion・Calendar・Drive/Sheets/Docs・GitHub）はしない。
- いまの止め手では足りない。`git-destructive-blocker` は保護ブランチへの push だけを見る。作業ブランチの push と PR 作成は止まらない。
- DWAI-api は develop への push で自動デプロイされる。夜に誤って push すると、他の人に見える本番へ反映される。
- 夜かどうかを人間が毎回指示するのは続かない。`~/.claude/night-mode.json`（マーカー）があれば夜間モード、という約束にして、止める側は hook に固定する。マーカーの書き手は work-agent 側（`workops night start|end`・ID46）。

## 決定

### マーカーの契約

- パスは `~/.claude/night-mode.json`（プロセスの HOME から解決する）。本人以外が場所を差し替えられる環境変数は設けない（抜け道になるため）。
- ファイルが無ければ OFF。hook は最初の検査でこれを見て、何も出さずに終了する。
- ファイルがあるとき、読めない・JSON でない・オブジェクトでない・`until` が無い・`until` にタイムゾーンが無い・日時として読めない場合は ON（安全側）。
- `until` が読めて、現在時刻が `until` より前なら ON。`until` 以降なら OFF（期限切れ。これが通常の自動解除）。
- `active` のような別のフラグは無い。終わらせるとは `until` を過去にすること。他のキーは情報用で、判定に影響しない。

### 夜間モード中に止めるもの（終了コード 2、理由は日本語で stderr）

- Bash:
  - git は既定で止める。通すのはローカル・読み取りのサブコマンドだけ: add・commit・status・log・diff・show・branch・checkout・switch・restore・reset・rev-parse・worktree・merge・rebase・cherry-pick・tag・fetch・pull・ls-files・grep・blame・init・clone・describe・shortlog・reflog・stash・rm・mv・revert・apply・am・format-patch・clean・rev-list・merge-base・ls-remote・cat-file・diff-tree・show-ref・for-each-ref・name-rev・bisect（`bisect run` は止める）。`config` は `--get`/`--get-all`/`--list`/`-l` のときだけ。`symbolic-ref` はオペランドが1つの読み取り形だけ。`remote` は引数なし・`-v`・`show`・`get-url` だけ。push・send-email・別名（`git p` など）・notes・未知のサブコマンド・`git config` の書き込みは止める。
  - 設定の上書き: サブコマンドより前の `-c`（`-cK=V` も）と `--config-env` は止める。`clone` 自身の `-c`/`--config` も止める。`git commit -c <commit>` や `git log -c` はサブコマンドの別のオプションなので通す。`--template`・`--upload-pack`・`--receive-pack`・`ext::` は全サブコマンドで、`rebase` の `-x`/`--exec`、fetch/pull/clone の `-u` も止める。長いオプションは前置きだけでも git に通じるため、危険な名前の前置き（2字以上。`--upl` など）と、束ねた短いオプションの各文字（`-ix`・`-qc`・`-pu`）も同じ扱いにする。
  - 環境変数: コマンド内に `GIT_*`・`EDITOR`・`VISUAL`・`SSH_ASKPASS`・`PAGER` の代入があれば止める（`env VAR=... git` や `export` も含む）。通すのは `GIT_EDITOR`・`GIT_SEQUENCE_EDITOR`・`EDITOR`・`VISUAL` が `true` か `:`、`GIT_PAGER`・`PAGER` が `cat`、`GIT_TERMINAL_PROMPT=0` だけ。
  - `g"it" push`・`\git push`・`git -C x push`・`sudo`/`doas`/`env`/`caffeinate`/`script`/`arch`/`watch`/`flock` 越し・`env -S`（引数を分け直して確認）・`sh`/`bash`/`zsh`/`dash`/`ksh`/`fish`/`csh`/`tcsh` の `-c` と `eval` の中・`&&` `;` `|` `$( )` の後ろも同じ形に直して判定する。入れ子の深さの上限を超えたら、通さずに止める。`sh -c -- '...'` のように `--` があっても `-c` の中身を取り出す。シェルは `-o`/`+o`/`-O`/`+O`/`--rcfile`/`--init-file` の値を飛ばしてスクリプトの引数を探し、実行するファイルがはっきりしなければ止める。大文字小文字は区別せずに比べる（macOS の既定のファイルシステムのため）。
  - 間接実行: コマンド内に git か gh がコマンドの語として現れるとき（`.git` のようなパスの一部は数えない）、`xargs`・`parallel`・`find -exec/-execdir/-ok/-okdir` は止める（何を渡すか追えないため）。標準入力からスクリプトを読むシェル（`... | sh`・`bash -s`・`bash < file`・`bash <<EOF`・`bash /dev/stdin`）も止める。スクリプトファイルの実行（`bash scripts/test.sh`）は通す（限界を参照）。
  - `gh` は既定で止める。通すのは読み取りだけ: `pr view|list|status|diff|checks`、`issue view|list|status`、`run view|list|watch`、`workflow view|list`、`release view|list|download`、`repo view|clone`、`auth status`、`search`、`api`（GET のみで、`-f/-F/--field/--raw-field/--input` なし）。
  - マーカー・設定・hook の改ざん: `night-mode`・`night_mode`・`nightmode` を含むコマンド（クォートとバックスラッシュを除いた形でも見る）、`workops ... night start|end`、`.claude/settings*`・`.claude/hooks` に触れるコマンドを止める。さらに、`.claude` を含むコマンドで（`.claude/worktrees/` の下はプロジェクトの作業ツリー置き場なので数えない。ホームの `~/.claude`・`$HOME/.claude`・`${HOME}/.claude` の下は `worktrees` でも数える）、変更系の語（rm・mv・cp・ln・find・tee・truncate・chmod・chflags・install・rsync・`sed -i`・`perl -i` など）かリダイレクト（`>`・`>>`。`2>&1` と `/dev/null` は除く）があれば止める。`.claude` やマーカーに当たりうるワイルドカード（`night*`・`*mode.json`・`.cl*`）も止める。`.git/config`・`.git/hooks/*`・`.git/info/*`（worktree・submodule の gitdir を含む）を書き換えるコマンド（変更系の語かリダイレクト）も止める。
  - 網（止めすぎを承知で張る）: 先頭のプログラムに関係なく、正規化した文字列（クォートとバックスラッシュを除き、大文字小文字を区別しない）で `git` の後ろに `push`/`send-email` がある、または `gh` の後ろに gh の書き込み形（`pr create|merge|review|comment|edit|close|reopen|ready`・`issue create|comment|edit|close`・`release create|edit|delete|upload`・`repo create|fork|delete|edit`・`workflow run`、`api` と `-X/--method` が GET 以外か `-f/-F/--field/--raw-field/--input`）があれば止める。`python -c`・`node -e`・`osascript`・未知のラッパーも同じ。`grep "git push" x` や `git commit -m "push の修正"` も止まる（止めすぎ。言い換えるか、メッセージをファイルに書いて `-F` で渡す）。
  - 作業ディレクトリ: hook の入力の `cwd` が、ホームの `.claude` の中、または `.claude/worktrees/*` 以外の `.claude` の中なら、すべてのコマンドに、`.claude` を含むときと同じ変更系・リダイレクトの検査をかける。ホームの `.claude` への `cd`/`pushd` も止める。
  - ローカルの git、テスト、ビルド、読み取りは通す。
- Edit / Write / MultiEdit / NotebookEdit: 対象がマーカー、どのディレクトリの `.claude/settings*.json`、どのディレクトリの `.claude/hooks/` 配下（プロジェクトの `.claude` も含む）、`.git/config`・`.git/hooks/*`・`.git/info/*` のとき。パスは `~` 展開・相対パス解決・シンボリックリンク解決のあとで比べる。
- MCP（`mcp__*`）: コネクタの名前空間は UUID で変わるため、最後の `__` より後ろの道具名で見る。
  - ローカルのサーバ（サーバ名のぴったり一致。`unityMCP`・`unityMCP-<名前>`・`ccd_*`・`visualize`・`Claude_Code_iOS_Simulator`・`scheduled-tasks`）は通す。ただし `ccd_session` の `move_to_cloud` と、`target` が `cloud`/`ssh` の `start_session`、`ccd_pr` の `set_auto_merge` は止める。
  - それ以外は、道具名が読み取りの動詞（get・list・read・search・fetch・query・view・find・retrieve・download・whoami・describe）で始まるときだけ通す。先頭が `slack`・`notion`・`api`・`gmail`・`calendar`・`drive`・`browser` のときは、2語目で見る。`API-post-search` だけは名前に post を含むが検索なので明示的に通す。
  - 読み取りの動詞で始まっても、名前に書き込みの動詞（create・update・delete・send・post など）を1つでも含めば止める（例: `get_or_create`）。
  - 上記以外の MCP は止める（既定で拒否）。
- Read・Grep・Glob・Agent など、その他のツールは通す。

### 置き場所

- claude-core に置く。claude-core は `~/.claude` へ入り、全セッションに効く層だから。
- claude-engineering は `--project` でプロジェクトごとにしか入らないので、「全セッション」の層になれない。

### 例外時の扱い（ADR-006 との違い）

- ADR-006 は、hook 自身の予期しない例外は exit 0（通す）と決めている。この hook は、**マーカーがある間に限り**逆にする。判定コードが例外を出したら、標準入力が壊れていたら、ブロックする（exit 2）。
- 理由: 夜間モードは「外に見える操作を絶対にしない」ための安全装置で、壊れて通すと、止めたかった操作が黙って通る。マーカーが無いとき（ふだんの昼）は従来どおり、何も起きずに通る。ふだんの開発を hook のバグで止めないというADR-006 の狙いはそのまま守られる。

### 人間の解除方法

- マーカーを、人間が自分のターミナルで削除する。または人間が `workops night end` を実行する。
- エージェントからは、マーカーの編集・削除、`workops night` の実行、設定ファイルと hook の編集ができない（上記のとおり止まる）。
- 何もしなくても、`until` を過ぎれば自動で解除される。

## 検討した選択肢

- **A. リポジトリごとの設定で止める** — 却下。DWAI の各リポジトリは他の人と共有しているため、リポジトリごとに設定を足す必要があり、置き忘れた場所では効かない。
- **B. claude-engineering に置く** — 却下。プロジェクトごとにしか入らず、全セッションの層ではない。
- **C. push と PR だけ止める** — 却下。Slack・Notion・Gmail・Calendar・Drive への書き込みは外に見えるのに、開いたままになる。
- **D. 全セッション層の hook で、外に見える操作をまとめて止める（採用）**。

## 結果

### Positive

- 夜は、push・PR・外への書き込みが、指示に頼らず物理的に止まる。
- マーカーが無いときの追加コストは、Python の起動時間にほぼ収まる（20 回の平均で、素の `python3 -c pass` は 27.9 ms、マーカー無しは 27.9 ms(再測定: 43.1 ms と 43.5 ms) で差が測れなかった。ON のときの Bash 判定は約 34 ms(再測定で +4 ms)）。

### Negative / 限界

- コマンド文字列を見る検査であり、網は意図的に不完全（ADR-028）。止められないもの:
  - スクリプトファイルの中身。`bash scripts/test.sh` は通す（テストやビルドを夜も動かすため）。その中に `git push` が書かれていても見ない。
  - インタプリタの中に隠した処理のうち、網（語の並び）にかからない形。語を分ける・変数で組む・ファイルに書いて実行する、`python3 -c` から別の外部書き込み手段（HTTP・`osascript` で Slack を操作するなど）を使う場合。`git push` や `gh pr create` の語がそのまま出る形は網で止まる。
  - ネットワーク道具での外部書き込み。`curl` での POST・webhook 呼び出し、`nc` など。
  - 変数や文字列の組み立てで作った語（`$X` に `git` を入れる、`.cl$Yaude` など）。
  - 別名にした `gh`（シンボリックリンクなど）。語を分けて作る呼び出し（`g=git; $g pu$x`）は網にも先頭語の検査にもかからない。
  - `git -C ~/.claude stash -u` など、git 自身による `.claude` への書き込み。`cwd` は hook の入力を信じており、`cd` が `.claude` の外の別名（シンボリックリンク）を経由する場合は見ない。
  - `GIT_EDITOR`・`GIT_PAGER` 以外の経路で、環境変数やファイルに仕込んだコマンド（設定ファイル・git の hook・エイリアスに前もって書かれたもの）。
- 止めすぎの整理（第2版で絞ったもの）: `.claude/worktrees/` 配下の作業ツリー、`git rm`・`mv`・`revert`・`apply`・`clean`・`remote -v`・`rev-list`・`merge-base`・`ls-remote` などのローカル git、`git commit -c`・`git log -c`、`GIT_EDITOR=true git rebase --continue`、パスの `.git` による `find -exec`/`xargs` は通すようにした。
- いま残る止めすぎ: 網のため、`grep "git push"` や `git commit -m "push の修正"` のように語が出るだけで止まる。許可リストにない git（`notes`・`remote add` など）。`.claude` を含むコマンド（作業ツリー置き場以外）に `install` や `>` が入っていれば止まる。`git rebase -x`・`git clone -c`。夜の作業の文字列に `night-mode` と書いても止まる。意図的な安全側の倒し方で、言い換えるかファイル経由（`git commit -F`）で避ける。
- 強い保証が要るなら、エージェントが書けないマーカーが要る（root 所有のファイルなど）。それには管理者権限のある人間の作業が要る。このとおり、文字列の検査は網であり、これ以上の穴ふさぎは足さない（ADR-028）。この hook は、その代わりの「うっかりと、よくある抜け道」を塞ぐ層。
- MCP の判定は、道具名の動詞による見立てで、確実ではない。読み取りに見える名前で書き込む道具、書き込みに見える名前の読み取り道具があると外れる。新しいコネクタは、夜は読み取りだけが通る側に倒れる（通らなければ昼にやる）。
- 夜間モード中は、Notion の記録や Slack の連絡も止まる。夜の作業の報告は、ローカルの作業ブランチとログに残し、朝に人間が出す。

### 運用上の影響

- `settings-fragment.json` に PreToolUse の項目を1つ足す。反映には `python3 install.py`（update）の再実行が必要（ADR-023）。配線は ADR-031 の所有 hook の入れ替えで他ツールの項目を残したまま入る。
- ヘルパは `hooks/_night_mode_policy.py`（マーカーの判定・ファイル・MCP）、`hooks/_night_mode_bash.py`（Bash の git・gh・シェル・間接実行）、`hooks/_night_mode_tamper.py`（マーカー・設定・hook の改ざん検出）。
