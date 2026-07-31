# ADR-025: 単一入口(`/autorun`)への統合と `loop-engineering` スキルの廃止

**ステータス**: accepted

**日付**: 2026-07-28

## コンテキスト

ADR-014は「Loop Engineering = 規律・原理そのもの」と定義し、`/autorun`（マクロ自走層）・
`skills/loop-engineering/`（ミクロ実装層）・`/review-loop`（レビュー層）を「同一原理の別スコープ
適用」として整理した。しかし実装レベルでは、コードを書く/直す依頼に対する能動発火の入口が
実質4つ独立して存在していた:

1. `skills/loop-engineering/` 自身の `description:`(「実装して/作って/修正して/直して/機能を追加して/
   バグを直して」等で起動)
2. `rules/agents.md`「Proactive Agent Invocation」表(requirements-analyst・task-analyst・planner・
   tdd-guide を個別に裸文言へ紐付け)
3. `/autorun` の明示コマンド起動
4. `workflows/loop-engineering-large-A.js` の独自経路(実装は`fixer`、計画は組み込み`Plan`エージェント
   を使用し、上記のいずれとも異なる担当者を割り当てていた)

この結果:

- 同じ依頼でも辿る経路によって挙動が変わる(明示コマンド有無で処理の重さが変わる、実行途中で
  モデル自身が場当たり的に `loop-engineering` を呼ぶ、等)。
- STEP0(サイズ判断)が `loop-engineering` の入口と `/autorun` の入口で二重化する。
- レビュー往復・完了判定が `loop-engineering` STEP5/6 と `/autorun` の独立した verify フェーズとで
  二重実行されうる(`/autorun` の `tdd` フェーズの success_test は機械的検証のみで、reviewer の
  `NO_ISSUES` 判定は含まれないにもかかわらず)。
- VISION述語の起草者が経路によって別人(`loop-engineering` 自身 / 組み込み `Plan` エージェント)に
  なる。
- `loop-engineering` というスキル名が、ADR-014が"原理の名前"として定義した語をコード段の1コン
  ポーネントが僭称する形になっており、Anthropic公式が"Loop Engineering"を特定ツールの固有名詞
  ではなく一般的な実践の名前として使っている用法とも整合しなかった。これが STEP0肥大化・
  「オーケストレータ」自称など、身の丈に合わない自己拡張の一因になっていた。

内容を棚卸しした結果、`skills/loop-engineering/` の STEP2-4(VISION起こし→観点→赤緑)は次を除き
ほぼ全て基盤内の既存パーツと重複していた: STEP4(赤緑)は `agents/tdd-guide.md` の RED→GREEN
手順とほぼ1:1、STEP3(N/E/B/S軸の観点)は tdd-guide の「Edge Cases You MUST Test」とほぼ同一機能。
残る独自技法は「後付けテストのミューテーションによる検出力の事後証明」1つのみだった。

## 検討した選択肢

1. **現状維持+ドキュメント整合のみ** — 各ファイルの矛盾する記述を辻褄合わせする。「明示するか
   しないかで挙動が変わる」問題は解消しない。
2. **`loop-engineering` スキルをリネームするに留める**(例: `code-loop`)— 名前の重力は軽減するが、
   入口の多重性・レビュー/完了判定の二重化・述語表起草者の不一致は残る。
3. **単一入口への統合+スキル廃止**(採用) — `/autorun` を唯一の能動発火先とし、サイズ判断を
   その入口に吸収する。`loop-engineering` スキルは中身をほぼ全て代替できるため廃止し、独自技法
   (ミューテーション事後証明)のみ `tdd-guide` に移す。

## 決定

**選択肢3を採用する。**

- **`/autorun` を、コードを書く/直す依頼(明示・裸文言を問わず)の唯一の能動発火先とする。**
  サイジング判断(C:些末→省略 / B:ミニ / A:フル、A内でのA-中小/A-大)はこの入口で一度だけ行う
  (`docs/autorun-flow.md`「Sizing」)。`rules/agents.md`の能動発火表は、requirements-analyst・
  task-analyst・architect・planner・tdd-guideを個別に裸文言へ紐付ける行を統合し、単一入口経由の
  1行にする。
- **`skills/loop-engineering/` を廃止する。** 独自技法だった「後付けテストのミューテーションに
  よる検出力の事後証明」は `agents/tdd-guide.md` に移植。
- **VISION述語表(ID+`[機械]`/`[AI]`タグ+N/E/B/S軸)の起草者を `agents/planner.md` に一本化する。**
  通常経路では `Success Criteria` セクションがこの表そのものになり、大規模経路
  (`workflows/large-scope-execute.js`、旧`loop-engineering-large-A.js`)では新設した
  fan-outサブモードが同じ表を並列・モジュール単位で起草する。
- **`agents/tdd-guide.md` を赤緑実行の唯一の担当にする。** 通常のtddフェーズでも、
  `large-scope-execute.js` のImplementフェーズ(旧`fixer`)でも同じ担当を使う。
- **`workflows/loop-engineering-large-A.js` は `large-scope-execute.js` に改名の上、維持する。**
  並列fan-out・決定的ID振り直し・RedGate・逐次実装というコードでしか担保できない不変条件は他で
  代替できないため。ただしagentType(`Plan`→`planner`、`fixer`→`tdd-guide`)と、廃止したスキルの
  STEPを直接名指ししていた内部の`nextStep`文言を配線し直した。
- **「Loop Engineering」という語は原理・実践の名前としてのみ残し、どの成果物(スキル・コマンド・
  workflow)の名前にも固定しない。** ADR-014の定義を、今回はファイル名のレベルでも徹底する。

## 結果

### Positive

- 依頼の言い回し(明示/裸)によらず同じ経路・同じサイジング判断に乗るため、挙動の不一致が構造的に
  起きなくなる。
- レビュー往復・完了判定の二重実行がなくなり、`/autorun`の往復予算(invariant 3)がtdd/verifyで
  正しく別会計になる。
- VISION述語表の起草者が経路によらず`agents/planner.md`に統一され、二重起草がなくなる。
- スキル1つ分のメンテナンス対象が減り、内容の重複(tdd-guideとの実質1:1重複)も解消。
- 「Loop Engineering」の名前がどの成果物にも固定されないため、ADR-014が懸念した「語の多義性に
  よる設計の取り違え」の再発を防ぎやすくなる。

### Negative

- `rules/agents.md`・`docs/autorun-flow.md`・`commands/{tdd,test-coverage,autorun,analyze-task,
  requirements,design}.md`・`docs/engineering-architecture.md`・`README.md`・`rules/loop-safety.md`・
  `agents/{tdd-guide,planner,architect,requirements-analyst}.md`・`workflows/large-scope-execute.js`
  など、参照箇所が多く波及範囲が広い(本ADRと同時にまとめて修正済み)。
- `agents/planner.md`が「通常の実装計画」と「large-A fan-out用のVISION起草」という2つのモードを
  持つことになり、単一責任の観点ではやや複雑になる(ただし起草者を1人に保つ利益がこのコストを
  上回ると判断)。

## 関連

- [ADR-014](./014-loop-engineering-as-discipline.md) — 「Loop Engineering=原理」の定義。本ADRは
  そのファイル名レベルでの徹底と、当時の監査(P3/P4)で先送りされていた重複の是正にあたる。
- [ADR-020](./020-thinking-tier-execution-guard.md) / [ADR-024](./024-sonnet-default-main-loop.md) —
  役割分担(Sonnet既定・思考ティアはエスカレーションのみ)。本ADRの実行主体には影響しない。
- `rules/loop-safety.md`「Single entry, single judge」— 本ADRが実装レベルで徹底した原則。
- `docs/autorun-flow.md`「Sizing」— 本ADRで新設したサイジング工程の正本。
