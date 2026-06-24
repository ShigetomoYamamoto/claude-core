# ADR-015: 人間ゲート極小の自走モード `/autorun --vibing` を採用する

**ステータス**: proposed

**日付**: 2026-06-21

## コンテキスト

[ADR-007](./007-autonomous-loop-execution.md) は「方向性＋不可逆操作で確認」（関門4点: 要件確定 /
設計確定 / PR作成 / デプロイ）を採用し、完全自走（選択肢3）を「最もリスク大」として却下した。これは
[ADR-014](./014-loop-engineering-as-discipline.md) の不変条件4（方向と不可逆は人間が所有）の帰結である。

一方で利用者から「リスクを理解した上で人間ゲートを極小化し、目的を1行渡したら完成まで一気に自走させたい」
というユースケース（高速試行・vibe coding 的な使い方）が出てきた。無印 `/autorun` はこの用途には人間介在
（関門4点）が多すぎる。

本 ADR は、無印 `/autorun`（ADR-007）を不変のまま残しつつ、**`--vibing` フラグ ON 時に限り ADR-007 の
関門設計を部分的に上書きする**第2の挙動を定義する。設計の出発点は「ゲートを消す」ではなく ADR-014 の
「ゲートは置くのでなく導出される（機械判定不能 or 不可逆 ⇔ 人間ゲート）」を維持したまま、**機械検証可能で
巻き戻し可能なゲートだけを auto へ降格する**ことである。

## 検討した選択肢

### フロー組込方式

1. **第3のモード行を追加** — full-auto/support に並ぶ vibing モードを新設。遷移表に行が増え、
   2モード×ゲート設計を3重に保守。重複大。
2. **full-auto/support 双方に乗る直交フラグ** — vibing は kind を降格する1段の変換（`resolve_kind`）。
   エンジンは1つのまま、RUN_STATE に vibing フラグを足すだけ。
3. **完全自走（ADR-007 選択肢3そのもの）** — 全ゲート撤廃。巻き戻し不能操作も止めない。

### PR→main 直結と `pr-base-checker.py`（develop ベース強制 hook）の衝突解消方式

- **B-1: hook に明示的 vibing 例外** — `pr-base-checker.py` がコマンド文字列内の vibing マーカーを見て、
  マーカー付き main PR のみ許容。gh CLI 経路＝物理層は生きたまま。
- **B-2: vibing は develop 自動マージにし main 直結 PR を出さない** — hook を変えないが「main 直結」を諦める。
- **B-3: MCP 経由で hook を回避** — 物理層を意図的に外す。ADR-008 の「push/PR は gh CLI 限定」方針に反する。

### vibing マーカーの実体

- **(A) コマンド文字列の末尾コメントマーカー** — hook が読む `tool_input.command` の末尾シェルコメントに
  名前空間付きトークンを置く。
- **(B) 環境変数** — hook が `os.environ` で読む。

## 決定

**フロー組込は選択肢2（直交フラグ）、PR 衝突は B-1（hook に明示的 vibing 例外）、マーカーは (A)
コマンド文字列内マーカーを採用する。**

### モードと起動

- `--vibing` は full-auto/support 双方に乗る直交フラグ。コマンドは `/autorun --vibing <目的>`。
  モード（full-auto / support）は無印 `/autorun` と同じく入力で自動判定する（具体タスク/Issue を渡せば
  support モードに vibing が乗る）。専用のモード上書きフラグは設けない。**無印 `/autorun` は ADR-007 のまま不変（後方互換）**。
- 隔離（worktree / staging 限定等）は必須前提ではなく**任意のオプトイン安全ダイヤル**（既定で強制しない）。

### kind 降格（`resolve_kind` による導出）

遷移表（`rules/autorun-flow.md`）の各行の `kind` は base 値のまま据え置き、kind 分岐の直前に
`resolve_kind(phase, state)` を1段挟む。vibing 適用後の各 phase の kind は次のとおり導出される:

| phase | kind_base | vibing 適用後 | 述語 |
|---|---|---|---|
| requirements | gate | **gate 維持** | 冒頭1回の方向確認（降格しない） |
| analyze-task | auto | auto | — |
| design | gate(skippable) | `design_needed ? gate : auto` | 新DB/新API/技術選定/境界変更が要るときのみ gate |
| plan / tdd / verify | auto | auto | — |
| commit | auto | auto | — |
| pr | gate | **auto（→main 直結）** | B-1 で hook 例外。物理層は gh CLI 経路で維持 |
| deploy | gate | `deploy_irreversible ? gate : auto` | auto-rollback 不能なら gate |
| migrate | auto/gate | `migrate_destructive ? gate : auto` | DROP/RENAME 等は gate |
| （外部送信 external_send） | — | gate | 巻き戻し不能は維持 |

→ **vibing が実際に外すのは「PR push」と「巻き戻し可能な deploy」だけ**である。requirements / design は
方向ゲートとして残り、巻き戻し不能操作（外部送信・破壊的 migrate・rollback 不能 deploy）も gate のまま残る。

### gate のまま残す停止点は2系統

1. **方向ゲート** — requirements（常時）と design（`design_needed` 真のときのみ）。機械判定できない方向判断。
2. **巻き戻し不能な不可逆操作** — 外部送信・破壊的 migrate（DROP/RENAME 等）・auto-rollback 不能な deploy。
   auto-rollback で取り返せないため。検出は機械判定述語で行い、**判定不能・取得失敗・解析エラーは
   fail-safe=gate（止める側）に倒す**。評価結果は毎回 transcript に出す。

### 不変条件の扱い

- **不変条件 1/2/3 は不可侵（維持）**。vibing が外すのは不変条件4 の**事前確認のみ**であり、その対象は
  「巻き戻し可能な不可逆/外向き操作（PR push・rollback 可能 deploy）」に限られる。
- 事前確認を外した代償として、不可逆操作には **事後監査＋auto-rollback（deploy-runner の検証失敗時
  ロールバック）＋transcript への実行記録**を維持する（ゲートではなくリスク緩和として）。
- vibing が安全に成立する前提は不変条件1（完了条件の機械チェック）が縦に閉じていること
  （要件 AC → tdd の VISION 述語 handoff、`rules/autorun-flow.md`）。これが壊れたら vibing は安全でなくなる。

### PR→main 直結（B-1 + マーカー (A)）

- `pr-base-checker.py` に「コマンド文字列の**末尾シェルコメント**に名前空間付きマーカー
  （`# __VIBING_AUTORUN_PR__`）を持つ `gh pr create --base main`（/master）のみ許容」する条件分岐を追加する。
  マーカー無しの非 develop base、およびマーカーが末尾コメント以外（`--title`/`--body` 等）に現れただけの
  場合は従来どおり exit 2（**fail-closed 維持**）。
- マーカーを (A) コマンド文字列に置く理由: hook は `tool_input.command` しか受け取らず、環境変数 (B) は
  autorun インタプリタ（Claude）から hook プロセスの環境へ確実に伝播できない（Bash 各呼び出しは別サブシェル）。
  (A) なら hook が既に読める情報だけで判定でき、実装が単純で決定的。
- **末尾コメント位置にアンカーする理由**: 単純な部分一致だと、公開済みのモード名が PR の title/body に
  紛れただけで develop 強制ガードが無効化される（accidental fail-open）。`#\s*__VIBING_AUTORUN_PR__\s*$` で
  末尾コメント位置にのみ一致させ、名前空間付きトークンにすることで散文混入を排除する。
- **この物理層は Bash(gh CLI) 経由にのみ作動し、MCP 経由 PR・deploy・migrate には作動しない**
  （`rules/agents.md` / `rules/loop-safety.md` の物理層スコープ）。過大表示しない。push/PR は gh CLI 固定を維持。

### ハードストップ（不変条件3 維持）

- vibing 専用に**全行程の遷移回数上限のみ引き上げる**（full-auto=24 / support=14）。
- **時間/トークンの session ceiling（既定 20ターン/30分）と per-phase（verify=5 / tdd 内部キャップ）は据え置き**。
- 従って実際には時間側が先に効いて goal 手前で止まりうる。これは不変条件3 が効いている証拠であり、
  自走の上限を撤廃したわけではない。

本 ADR は **vibing フラグ ON 時に限り ADR-007 を部分 supersede** する。無印 `/autorun` は ADR-007 のまま生きる。

## 結果

### Positive

- 既存エンジンに直交フラグを1段足すだけで実現でき、保守箇所が最小（遷移表は不変、RUN_STATE に
  vibing を足し `resolve_kind` を1段挟むのみ）。
- 無印 `/autorun` の関門4点設計は完全に保たれる（後方互換）。
- 不変条件1/2/3 を保つため、人間の事前確認を外しても「機械が下で必ず検証する」閉ループは生きる。
- 巻き戻し不能操作（外部送信 / 破壊的 migrate / rollback 不能 deploy）は gate 維持＋fail-safe=gate で、
  取り返しのつかない事故の確率を抑える。
- 実際に外す事前確認は「PR push」「巻き戻し可能な deploy」のみに限定され、当初想定の「完全自走」より
  安全側に収束した。

### Negative

- 不変条件4 の事前確認を一部外す＝**残存リスクを利用者が引き受ける**モードである（PR push・rollback 可能
  deploy の事前人間確認が消える）。事後監査と auto-rollback が最後の砦になる。
- 巻き戻し不能操作の検出述語（`migrate_destructive` / `deploy_irreversible` / `external_send`）が
  **停止ホワイトリストの単一障害点**。誤検出（本来 gate を auto に倒す）は事故に直結するため fail-safe=gate で
  保守的に倒すが、述語のメンテが品質を左右する。
- 外部送信・migrate・deploy の gate は**物理層を持たない**（手続きのみ）。hook は gh CLI 経由の git/PR にしか
  作動しない。この限界を運用者が理解している必要がある。
- vibing マーカーはコマンド文字列に置くため、原理的には人間/エージェントが**末尾コメントに**同じトークンを
  意図的に手打ちすれば develop 強制をすり抜けられる（物理的完全防御ではない）。ただし末尾コメント位置への
  アンカーと名前空間付きトークン（`__VIBING_AUTORUN_PR__`）により、散文・title/body への偶発混入による
  fail-open は排除済み。残るのは「意図的な手打ち」のみで、これは vibing 以外がトークンを発行しない運用規律で抑える。
- `pr-base-checker.py` の不変条件が「develop のみ」から「develop もしくは vibing マーカー付き main」へ
  1条件拡張され、hook の単純さが僅かに下がる。

## 関連

- [ADR-007](./007-autonomous-loop-execution.md) — 関門4点・完全自走却下（本 ADR が vibing 時に限り部分 supersede。
  requirements/design は維持し、PR・rollback 可能 deploy を降格）
- [ADR-008](./008-orchestration-declarative-flow.md) — 宣言的フロー方式（vibing もこの基盤に乗る。
  push/PR は gh CLI 限定の方針を継承）
- [ADR-014](./014-loop-engineering-as-discipline.md) — 四不変条件（vibing が外すのは不変条件4 の事前確認の一部のみ、
  1/2/3 不可侵）
- `rules/autorun-flow.md` — vibing 降格ルール（`resolve_kind` 導出表）の正
- `rules/loop-safety.md` — 不可逆操作の vibing 分岐・残存リスクの正
- `commands/autorun.md` — `--vibing` の解釈（薄い起動器、定義は上記2ファイル参照）
- `hooks/pr-base-checker.py` — vibing マーカー付き main PR の許容（物理層）
