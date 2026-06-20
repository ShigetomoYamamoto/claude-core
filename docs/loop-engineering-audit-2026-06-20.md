# Loop Engineering 適合監査記録(2026-06-20)

[ADR-014](./adr/014-loop-engineering-as-discipline.md) で確定した骨格(4不変条件・再帰モデル・入口一元化/判断者1人・ゲート導出)に対し、全資産(agents 16・commands 23・skills 3・workflows 1・hooks 8・rules 12 ≒ 63ファイル)を「5問の篩」で監査した記録。読み取り専用エージェント6体で分担評価し、結論を左右する重い判定は実ファイルで裏取り済み。

## ⚠️ 追記(同日・コードレビューによる訂正)

**本監査は「適合性監査(5問の篩)」であり、コード品質レビューではない。** その限界が露呈した:
骨格整合の修正後に独立 `reviewer`(maker≠checker)で `workflows/loop-engineering-large-A.js` と
`hooks/mass-delete-blocker.py` を厳密レビューしたところ、**CRITICAL 2・HIGH 2** の実バグが見つかった
(適合性監査では検出できていなかった):

- **CRITICAL** `mass-delete-blocker.py` の rm 検出正規表現 `…|…` が未グルーピングで第2枝が rm を要求せず、
  `docker run -fr` 等を誤検出(自走時は ask→deny で無害なコマンドが停止)。
- **CRITICAL** root/home の即ブロックが `rm -rf /*` / `"/"` / `/usr` を取りこぼし、最も破滅的な削除が ask 止まり。
- **HIGH** 分離/大文字フラグ `rm -r -f` / `-fR` を検知できず素通り(docstring の約束と不一致)。
- **HIGH** `loop-engineering-large-A.js` 実装ループが `agent()` の null を握り潰し、verify_failed に化けて誤誘導。

→ いずれも修正済み(hook はトークン解析へ書き直し29ケースで検証、workflow は null ガード追加・`A`→`parsedArgs` 改名)。
**教訓: 適合性監査の後は必ずコードレビュー(reviewer)を回す。** 下表の「残す/確信度高」は
「骨格に適合」の意味であって「コードが無欠陥」ではない。

## 5問の篩

1. どの段(rung)の実装か?
2. 4不変条件に適合するか?違反は?
3. 「判断者は1人」に反していないか?(scope/サイズ判断の二重化)
4. ゲートが導出ルールと一致するか?(人間停止が "機械判定不可 or 不可逆" と一致)
5. 重複していないか?

判定ラベル: `残す` / `再定義して残す` / `統合` / `廃止` / `穴(不足)`

## 集計

- **廃止:0件**(骨格に照らして捨てるべき資産は無い)
- **残す:約40件**
- **再定義して残す:約17件**
- **統合:約6件**

結論: 既存実装はほぼ再利用できる。問題は部品の質ではなく、骨格(4不変条件)の未明文化と適用の不一致。是正は8パターンに収束する(ADR-014 参照)。

## 裏取り済みの重要判定(確度:高)

| 主張 | 実ファイル確認 | 結果 |
|---|---|---|
| security-reviewer が不変条件2違反 | `tools: Read, Write, Edit, Bash, Grep, Glob`(L4)。対し reviewer は `Read, Grep, Glob, Bash` | ✅ 検出と修正が同一主体 |
| mass-delete-blocker が止めない | ルート/HOME のみ exit 2、通常 `rm -rf` は warning のみ exit 0(L24) | ✅ 不可逆なのに素通り |
| secret-detection が止めない | `exit 2` なし、print のみ(L31-33) | ✅ 検出器でブロッカでない |
| verify-loop がフロー未配線 | autorun-flow / autorun / skill から参照ゼロ。README・requirements.md・ADR-007 のみ | ✅ かつ requirements.md と autorun-flow が矛盾 |
| loop-safety に不変条件2が無い | 前提は4つ(完了条件/作業場/機械テスト/ハードストップ)で maker≠checker の明文なし | ✅ |

## ① ループ機械本体(8)

| ファイル | 段 | 判定 | 要点 |
|---|---|---|---|
| rules/autorun-flow.md | 全段の遷移表 | 残す | gate が「機械判定不可 or 不可逆」と一致。重複なし |
| commands/autorun.md | インタープリタ | 残す | success_test を機械実行・自己申告で代替しない。委譲で重複回避 |
| commands/review-loop.md | レビュー段 | 残す | maker(fixer)≠checker(reviewer)を分業強制。レビュー段の正本 |
| commands/verify-loop.md | レビュー段(上位変種) | 再定義して残す | review-loop と二重。フロー未配線の孤児。反証多数決のみが差別化(P7) |
| commands/review-loop-cross.md | レビュー段(モデル分離) | 残す | checker を別モデルにし不変条件2を最強化。外部CLIは人間確認 |
| commands/review-loop-cross-path.md | レビュー段(パス指定) | 残す | 非git/差分なしの穴を埋める正当分岐 |
| skills/loop-engineering/SKILL.md | コード段+完了判定の統括 | 残す | VISION=不変条件1。STEP0 の二重判断リスクは P4 で是正 |
| workflows/loop-engineering-large-A.js | コード段(A-大) | 残す(要コード修正→済) | RedGate・戻りチャネル等の決定的ガード。レビューは委譲。※同日コードレビューで実装ループの null 握り潰し(HIGH)を修正・`A`→`parsedArgs` 改名(上「追記」参照) |

## ② 上段ラダー: 要件/設計/計画(8)

| ファイル | 段 | 判定 | 要点 |
|---|---|---|---|
| agents/requirements-analyst.md | 要件 | 残す | 完了=人間承認(L101-107)。不変条件4に適合 |
| agents/task-analyst.md | 要件(support) | 再定義して残す | full-auto/support の振り分けが2エージェントに分散(P4) |
| agents/architect.md | 設計 | 再定義して残す | Phase 1 が要件段を再実装。人間ゲート内在化なし(P8) |
| agents/planner.md | 計画 | 残す | file path + ordered steps を必須化。flow と一致 |
| commands/requirements.md | 要件 | 統合 | agent の薄ラッパー(P5) |
| commands/analyze-task.md | 要件(support) | 統合 | agent の薄ラッパー(P5) |
| commands/design.md | 設計 | 統合 | agent の薄ラッパー(P5) |
| commands/plan.md | 計画(+入口判断) | 再定義して残す | 設計要否を autorun-flow と二重判定(P4) |

## ③ コード/レビュー段(8)

| ファイル | 段 | 判定 | 要点 |
|---|---|---|---|
| agents/tdd-guide.md | コード | 再定義して残す | loop-engineering STEP4 と二重。単体で有界なし(P2/P3) |
| agents/reviewer.md | レビュー(checker) | 残す | Edit/Write 無しで分離を構造担保。不変条件2の正実装 |
| agents/fixer.md | レビュー(maker) | 残す | Edit/Write 保持で reviewer と権限分離。公式重複なし |
| agents/build-error-resolver.md | コード(ビルド緑) | 残す | 有界は build-fix 側(P2 で明記補強) |
| agents/security-reviewer.md | レビュー(セキュリティ) | 再定義して残す | Write/Edit 保持=検出と修正が同一(P1)。有界なし(P2) |
| commands/tdd.md | コード入口 | 統合 | 二つ目の入口。サイズ判断をバイパス(P3) |
| commands/test-coverage.md | コード(カバレッジ) | 統合 | 独立段でない。完了判定の一部(P3) |
| commands/build-fix.md | コード入口 | 残す | L14 で3回停止=有界を補完 |

## ④ 出荷/運用段(10)

| ファイル | 段 | 判定 | 要点 |
|---|---|---|---|
| agents/deploy-runner.md | 出荷(デプロイ) | 再定義して残す | 有界なし(P2)。本番ゲートが手続きのみ・物理層なし(P6) |
| agents/migration-runner.md | 出荷(マイグレ) | 再定義して残す | 破壊的=不可逆の人間ゲートが手続きのみ(P6)。有界なし(P2) |
| agents/rollback-runner.md | 出荷(ロールバック) | 再定義して残す | 物理層なし(P6)。flow 未登録=手動専用の明記要(穴埋め) |
| agents/review-responder.md | レビュー隣接(応答) | 残す | review-loop と方向が逆で重複なし |
| commands/deploy.md | 出荷 | 残す | agent の弱点を継承するのみ(薄い委譲) |
| commands/migrate.md | 出荷 | 残す | 同上 |
| commands/rollback.md | 出荷 | 残す | 同上 |
| commands/respond-review.md | レビュー隣接 | 残す | 公式 pr-review-toolkit と方向が逆 |
| commands/create-branch.md | 出荷前段(可逆) | 残す | ADR-012 で自作維持。公式に同等品なし |
| commands/create-pr.md | 出荷(PR) | 残す | 物理+手続きの二重で不変条件4を実装=この段の手本(軽微:ステップ番号欠番・code-reviewer 表記) |

## ⑤ 補助系(10)

| ファイル | 段/横串 | 判定 | 要点 |
|---|---|---|---|
| agents/doc-updater.md | 横串(doc同期) | 再定義して残す | 検証が自己申告。機械検証へ寄せる余地 |
| agents/e2e-runner.md | 横串(機械検証手段) | 残す | Playwright が ○× を出す。不変条件1に合致 |
| agents/refactor-cleaner.md | 横串(掃除) | 残す | 削除毎に機械検証。バッチ=有界 |
| commands/e2e.md | 横串入口 | 残す | 薄い委譲 |
| commands/update-docs.md | 横串入口 | 残す | 薄い委譲 |
| commands/update-codemaps.md | 横串入口 | 統合候補 | update-docs と同一 doc-updater を起動 |
| commands/refactor-clean.md | 横串入口 | 残す | 薄い委譲 |
| commands/init-autonomous.md | 規律外(基盤生成) | 再定義して残す | 規律を新repoへ敷設するブートストラップ |
| skills/3-line-contract/SKILL.md | 入口前段 | 残す | loop-engineering が STEP1前段で参照済み |
| skills/git-workflow/SKILL.md | 横串(参照資料) | 残す | commit/branch/PR フォーマットの正本 |

## ⑥ 横串=安全の憲法 + 物理層(19)

| ファイル | 種別 | 判定 | 要点 |
|---|---|---|---|
| rules/loop-safety.md | 横串(安全)=中核 | 再定義して残す | 不変条件2が未定義(P1) |
| rules/agents.md | 横串(オーケストレーション) | 再定義して残す | ブランチ保護のソフト/ハード層の役割が未明記(P6) |
| rules/git-workflow.md | 横串(安全) | 残す | 振る舞い=公式委譲/決定的ブロック=hooks を明記済み |
| rules/coding-style.md | 前提 | 残す | 検証段の合否述語を供給 |
| rules/testing.md | 前提+合否定義 | 残す | 80%カバレッジ・TDD=不変条件1の供給源 |
| rules/security.md | 横串(安全) | 残す | 秘密の層マップ追記で補強(P6) |
| rules/answer-only.md | 横串(入口規律) | 残す | 不変条件4の入口側実装 |
| rules/memory.md | 横串(メモリ) | 残す | アウターループの唯一規範 |
| rules/parallel-worktree.md | 横串(並列) | 残す | writer隔離の唯一規範 |
| rules/claude-efficiency.md | 前提(コスト) | 再定義して残す | モデル世代記述が陳腐化リスク |
| rules/patterns.md | 前提(着手手順) | 再定義して残す | 骨格内の居場所が曖昧 |
| hooks/commit-msg-convention.py | 物理層(規約) | 残す | 自認:安全装置でなく規約チェック。fail-open |
| hooks/doc-blocker.py | 物理層(生成抑制) | 残す | 規範のハード化 |
| hooks/git-add-secret-blocker.py | 物理層(不可逆=漏洩防止) | 残す | 効く/効かない範囲を明示=模範 |
| hooks/git-destructive-blocker.py | 物理層(不可逆ブロック中核) | 残す | 保護ブランチ/force push/reset --hard 等を exit 2 |
| hooks/mass-delete-blocker.py | 物理層(確認ゲート) | 再定義済み(要バグ修正→済) | 非ルートの再帰削除・閾値超ワイルドカード削除を `permissionDecision=ask`、root/system/home は exit 2。※同日コードレビューで正規表現の誤検出/取りこぼし(CRITICAL×2・HIGH)を修正し、単一正規表現→トークン解析へ。29ケースで検証(上「追記」参照) |
| hooks/pr-base-checker.py | 物理層(PR=外向き) | 残す | develop 強制。MCP 経由は対象外(範囲明示済み) |
| hooks/protected-branch-edit-guard.py | 物理層(予防) | 残す | 保護ブランチ上の Edit/Write を exit 2 |
| hooks/secret-detection.py | 物理層(検出・非ブロック) | 再定義して残す | exit 2 なし=検出器。名と層を明示(P6) |

## 横断的な穴(不足)

- **要件→VISION の受け渡し契約が未定義**: 上段(要件)の受け入れ基準が、下段(コード段)の機械判定述語(VISION)へ変換される連結が明文化されていない。閉じたループを上段から下段へ繋ぐ契約が穴。
- **不可逆出荷3点(deploy/migrate破壊的/rollback)の物理層が無い**: create-pr が物理+手続きの二重で守られるのと対照的に、最も不可逆な操作が最も弱い。loop-safety の既知限界だが、各 agent が "CONFIRM" を断言形で書くため誤認を招く。
- **物理層の効く範囲が loop-safety の autorun節にしか無い**: Bash経由のみ・MCP/deploy は対象外、という一般原則への昇格が必要。
