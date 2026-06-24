# ADR-018: pushed/merged 成果物の done-condition に remote CI green を含める

**ステータス**: proposed

**日付**: 2026-06-24

## コンテキスト

`/autorun --vibing`（support モード, goal=pr）でプロダクト実装を連鎖させる中、PR を **GitHub Actions の CI 結果を一度も確認せずに** develop へ連続 merge する事故が起きた。別件の CI 設定バグで CI が赤のままでも、全 PR が素通りした。「ローカルで test/typecheck green ＝ merge してよい」という運用になっていた。

根本原因はハーネスの設計にある:

1. autorun の各 auto フェーズの success_test が「ローカル機械実行（test/lint/typecheck）＋ reviewer」だけで定義され、**remote CI green が done-condition に入っていない**（`rules/autorun-flow.md` の遷移表 verify/commit/pr、`commands/autorun.md` step 4.3「機械的に実行」、`rules/loop-safety.md` Precondition 3 がいずれもローカル前提）。
2. `--vibing` の `resolve_kind` が `pr` ゲートを auto に降格する。無印では `pr` が gate なので人間が PR 画面で CI を一瞥できたが、vibing はその人間を外す。**外した人間の代わりに機械側へ CI チェックを引き継いでいなかった**ため、誰も CI を見ない経路が完成した。
3. 「止まってよい場所のホワイトリスト」に「CI 赤 / CI 未完了」が無く、赤でも停止理由にならなかった。support+vibing は goal=pr であり「merge」はフロー上の正式フェーズですらない（連鎖のため develop へ merge していたが、その merge に対する機械ゲートが未定義）。

これは [ADR-014](./014-loop-engineering-as-discipline.md) の**不変条件1（done-condition は upfront・machine-checked・un-fakeable）の取りこぼし**である。ローカル green は un-fakeable ではあるが、チームが実際に正としている remote CI の真実と乖離しうるため、**完了条件として不十分**だった。「機械検証はしていた」が、検証していた対象が*本当の*完了条件ではなかった。

[ADR-015](./015-vibing-mode.md) の決定どおり **vibing が外すのは不変条件4（人間の事前確認）だけで、不変条件1（機械検証）は不可侵**であり、むしろ vibing の安全性の根拠である。したがって remote CI green を機械 success_test に組み込むことは vibing の趣旨と矛盾せず、これを補強する。

## 検討した選択肢

1. **(A) success_test に「remote CI green」機械成分を追加し、merge を横断規律で、CI 赤/未完了を停止ホワイトリストで担保する** — 遷移表の `pr` success_test に機械成分を足し、起動時チェックで CI 実在を検出し、共有ブランチ merge は CI green 必須の横断ルール（loop-safety.md）で縛る。エンジン・遷移表の骨格は不変。
2. **(B) 遷移表に新 `ci` フェーズを追加** — pr の後に ci フェーズを挿入。明示的だが遷移表が膨らみ、CI が PR 駆動で「pr の後にしか存在しない」実態（pr の成果が CI を起動する）とフェーズの直線性が噛み合わない。support の goal=pr 定義ともぶつかる。
3. **(C) CI 確認の人間ゲートを新設** — CI 結果を人間が確認するゲートを置く。だが CI green は**機械判定可能**であり、ADR-014「ゲートは置くのでなく導出される（機械判定可能なら機械側へ）」に反する。vibing の趣旨（機械検証は外さない）とも逆行。

## 決定

**選択肢 (A) を採用する。** remote CI green を「人間ゲート」ではなく「機械 success_test」として表現する。

### success_test への機械成分追加（`rules/autorun-flow.md`）

- `pr` フェーズの success_test を **「remote CI green（機械）＋ human approves the PR（push/PR は gh CLI）」** の2成分にする。CI は PR push 後に起動するので、PR 作成 → CI 起動 → green 待ち、の順で機械確認する。
- 起動時の「機械検証可能性チェック」を拡張し、`.github/workflows/` に PR/push トリガの CI が実在するかを検出する。実在すれば pr の success_test に CI green を必須化する。**CI が無いプロジェクトは待つものが無いので skip するが、その旨を transcript に必ずログする**（「CI 未検出のため CI green チェックなし」）。

### CI 待ちの機構と fail-safe（`commands/autorun.md`）

- PR 作成後・前進（full-auto は migrate へ）または共有ブランチへの merge 前に、`gh run watch <run-id> --exit-status`（または `gh pr checks <pr> --watch`）で green を機械確認する。
- **green → 前進。赤 / タイムアウト / run 検出不能 → STOP・報告（fail-safe=停止）**。不変条件1を un-fakeable に保つため、判定不能は止める側へ倒す。
- これは **「手続き＋機械チェック」で担保し、物理層（hook）は無い**。hooks は Bash 経由の git/PR にしか作動せず CI 待ちには作動しない。過大表示しない。

### merge の扱い（`rules/loop-safety.md` 横断規律）

- support+vibing の goal は pr であり merge はフェーズではない。連鎖のための develop merge は文脈依存に起きるため、**「共有ブランチ（develop/main）への merge は head の remote CI green を機械確認してから行う」横断規律**で縛る（フェーズ化しない）。

### vibing との関係（不変条件1は降格しない）

- `resolve_kind` が `pr` で降格するのは **人間の事前確認（gate 成分）のみ**。**remote CI green の機械 success_test 成分は不変条件1であり降格対象外**。よって vibing でも pr→auto は CI green を待ってからでないと前進・merge しない。
- 停止ホワイトリストに「remote CI 赤 / CI 未完了（pr 前進点・共有ブランチ merge 点）」を追加し、**この停止は vibing でも外れない**（vibing が外すのは事前確認であって機械検証ではない）。

## 結果

### Positive

- 不変条件1の done-condition が remote CI まで縦に閉じ、「ローカル green ＝ merge 可」の穴が塞がる。
- 新しい人間ゲートを置かないため、ADR-014「ゲートは導出される」と整合し、vibing の高速性（人間の事前確認を外す）も保てる（外すのは人間確認、保つのは機械検証）。
- 遷移表の骨格・エンジンは不変で、success_test の成分追加・起動時チェック拡張・横断規律1本・停止WL1項目のみの最小変更。

### Negative

- CI 待ちには**物理層が無い**（手続き＋機械チェックのみ）。hook は CI 待ちに作動しないため、autorun インタプリタ（Claude）の遵守に依存する。この限界を運用者が理解している必要がある。
- `gh run watch` のタイムアウト・CI 検出のヒューリスティック（どの run が「この PR の」CI かの同定）に運用上の手当てが要る。fail-safe=停止で安全側に倒すが、誤って停止し過ぎる可能性はある。
- CI 起動の遅延ぶん、pr フェーズの実時間が伸びる。session ceiling（20ターン/30分）に当たりやすくなるが、これは不変条件3が効いている挙動であり許容する。

## 関連

- [ADR-007](./007-autonomous-loop-execution.md) — 関門4点（pr ゲート）。本 ADR は pr の success_test に機械成分を足すが、人間ゲート（無印）は不変。
- [ADR-014](./014-loop-engineering-as-discipline.md) — 四不変条件。本 ADR は不変条件1（machine-checked done-condition）の縦の閉じを remote CI まで延ばす。
- [ADR-015](./015-vibing-mode.md) — vibing は不変条件4の事前確認のみ外し 1/2/3 は不可侵。本 ADR の CI green 機械成分は降格対象外、という整合をここで確定する。
- `rules/autorun-flow.md` — success_test・起動時チェック・停止WL・vibing 降格の正。
- `commands/autorun.md` — CI 待ち機構の手続き。
- `rules/loop-safety.md` — Precondition 3・merge 横断規律・停止WL の正。
