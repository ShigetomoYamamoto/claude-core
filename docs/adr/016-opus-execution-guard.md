# ADR-016: Opus 実行防御 — 思考と実行の役割を機械的に分離する

**ステータス**: Accepted

**日付**: 2026-06-23

## コンテキスト

Claude の複数モデル間での役割分担について、次の要望が出た:
「Opus は思考(相談・調査・プラン・委譲)に使い、Sonnet は実行操作(編集・変更系 Bash・反復作業)に使い分けたい。Opus の編集/削除は Hook で禁止する」。

本質は「思考が要らない実行作業は低コストモデル(Sonnet)に任せる」だが、手動での `/model sonnet` 切り替えはユーザー負担になる。そこで **Opus の実行ツール操作をいつでも Hook で自動的にブロックする**仕組みを検討した。

### 検証済み技術事実

1. **PreToolUse stdin に model は来ない** — `agent_id` / `agent_type` / `effort` は含まれるが、実行中のモデル識別子 (`model: "claude-opus-..."`) は Hook の stdin に渡されない。
2. **transcript の `message.model` が唯一の信頼源** — Bash/Edit/Write 実行時に Hook が読める情報は tool_input のみだが、Tool Use 直前の transcript には最新の assistant message があり、その `message.model` フィールドで現在のアクティブモデルが判定できる。
3. **settings.json に model キーなし** — Claude Code の設定は model 属性を記録しない。`/model sonnet` の実行時切替も settings に反映されない。
4. **サブエージェント中の Hook はサブ自身のモデルを見る** — stdin に `agent_id` があれば、その Hook は Bash を実行したサブの model(RUN_STATE)を見る。メインの model ではなく。
5. **Hook の作動範囲は機械的に限定** — PreToolUse Hook は Bash と Edit|Write|MultiEdit|NotebookEdit ツールにのみ作動(settings の matcher)。MCP 経由のツール操作・deploy/migrate/rollback コマンドには作動しない([ADR-014](./014-loop-engineering-as-discipline.md) に同調)。

## 検討した選択肢

1. **stdin の model を待つ** — PreToolUse API に model が来るまで待つ。課題: 来ない。技術的に回避不可。
2. **settings.json に model を記録** — Hook が settings を見て判定。課題: キーが無く、実行時切替(`/model sonnet`)が反映されない。検証済みで確実性がない。
3. **fail-closed (全ブロック)** — Opus に限定せず**全モデルの実行を Hook で止める**。課題: [ADR-006](./006-hook-error-policy.md) の fail-open 方針に矛盾。正常系の開発全停止リスク。
4. **fail-open のみ(Hook なし)** — エージェント model 明示(`model: sonnet`)とコマンド `--vibing` や Agent tool の model パラメータで振り分け。課題: **手動チャットでの Opus 編集を止められない** → 要望を満たさない。最後の砦がない。
5. **PostToolUse で検知** — 編集実行後に Hook で検知。課題: 既に書き込みが完了している。詰まった時点で遅い。

**選択肢 1～5 を排除し、以下の**複合策**を採用:**
- transcript の `message.model` に依存することで、リアルタイムかつ信頼性を確保。
- サブエージェント(stdin に `agent_id` 有)は委譲層とみなし、**無条件に許可** → transcript_path 判定の不確実性に非依存。これで「サブの transcript がどちらを指すのか」の make-or-break を回避。
- メインループ(agent_id 無)の Opus のみを Hook で ブロック → エージェントロールの role separation は別ルールで補完。
- 判定不能・パース失敗は fail-open → ADR-006 と一貫。

## 決定

### 1. 新規 PreToolUse Hook `hooks/opus-execution-guard.py`

**監視対象:**
- ツール: `Edit`・`Write`・`MultiEdit`・`NotebookEdit`(編集系4種)
- Bash コマンド: 変更系(rm/mv/sed -i/npm install 等)

**判定ロジック:**
1. stdin に `agent_id` 有 → **許可**(サブエージェント委譲層。その model は RUN_STATE に既にある)
2. stdin に `agent_id` 無かつ `tool_name` が編集系4種 OR Bash 変更系 → transcript 末尾から直近 assistant を逆順走査
3. `message.model` が `claude-opus-*` で前方一致 → **exit 2 (ブロック)**
4. それ以外(`claude-sonnet-*` / `claude-haiku-*` / 判定不能) → **exit 0 (許可)**

### 2. サブエージェント文脈の無条件許可

stdin に `agent_id` / `agent_type` が有る場合、メイン model がなんであろうと常に pass(exit 0)。
- **根拠**: Hook は Bash と Edit|Write に作動するだけであり、サブエージェント実行中の Bash/Edit はサブが RUN_STATE で渡した model を持つ。その model の制御は `/autorun` / Workflow / Task の起動時に `model: sonnet` 明示で担保(既存の編集系エージェント全て済み)。
- **効果**: transcript_path 解決への依存性を設計から消す(実機確認の make-or-break を回避)。

### 3. メインループの transcript 逆順走査

サブエージェント文脈でない場合、transcript 末尾(64KB窓)を逆順走査し直近 assistant の `message.model` を取得:
```python
for line in reversed(transcript_lines):
    try:
        obj = json.loads(line)        # 壊れた行は skip
    except Exception:
        continue
    if obj.get("type") == "assistant":
        model = obj.get("message", {}).get("model")
        if model:
            break
```
判定不能(assistant なし、model フィールド欠落、パース失敗)は fail-open → **exit 0**。

### 4. Bash 変更系の判定

denylist による light control(完全な shell パース不可、shadow cases あり):
- ✓ 捕捉: `rm` `rmdir` `mv` `cp` `tee` `mkdir` `touch` `sed -i` / `git add|commit|push|reset|clean|checkout|restore` / `npm|pip install` / リダイレクト `>` `>>` 等
- × 取りこぼし可(fail-open 側): `sudo rm` / `xargs rm` 等の接頭辞付き / `find . -delete` / `2> file` のような fd 番号付きリダイレクト / 間接呼び出し(script ファイル)
- × 誤ブロック可(fail-closed 側): `echo "a > b"` のような文字列内の `>`、`echo "rm -rf /"` のような文字列内コマンド

設計として light control で許容(完全防御は不可能で、fail-open に倒す。開発停止リスクが重大)。

### 5. ロール分離は Hook + 規範 + エージェント明示

MCP/deploy/migrate には Hook が作動しない([ADR-014](./014-loop-engineering-as-discipline.md) 物理層スコープ)ため、これら実行系は:
- **規範層**: `rules/role-separation.md` 新設(Opus=思考 / Sonnet=実行)
- **実行エージェント層**: `model: sonnet` の明示を編集系全エージェントで確認・維持(既存達成率 100%)

### 6. loop-engineering Skill の注記

STEP4(実装ステップ)に **ADR-016 モデル役割ガード注記**を追加:
> Opus 実行時は `opus-execution-guard` が編集系/Bash ブロック → Sonnet へ `/model sonnet` 切り替え or サブエージェント委譲。

既存「分離はしない」設計と矛盾させない書き方にする。

## 結果

### Positive

- **役割分担が機械的に強制される** — Opus 手動チャットでの「ついうっかり編集」を防止。
- **hook は exit 規約に一貫**(ADR-006) — 他の Hook と同じ exit2 / exit0 体系で統一。
- **fail-open で誤判定時も開発が止まらない** — [ADR-006](./006-hook-error-policy.md) に準拠。開発全停止(fail-closed)リスク排除。
- **agent_id ゲートで transcript_path 解決に非依存** — サブエージェント delegate 層の model は既に RUN_STATE で制御。実機確認の不確実性(make-or-break)を設計段階で消す。
- **複層防御で堅牢** — Hook(強制) + 規範(role-separation.md) + エージェント model 明示(既存達成)で三重。

### Negative(限界を正直に)

- **未文書の transcript JSONL フォーマットに依存** — `message.model` は Claude Code 内部仕様。API 変更で壊れうる。対策: fail-open + テスト + 定期確認で影響を限定。恒久保証ではない。
- **Bash denylist は不完全** — (a) `sudo rm` / `xargs rm` / `curl | sh` 等の接頭辞・パイプ型削除は取りこぼし(fail-open 側)。(b) `echo "rm -rf"` のような文字列内コマンドで稀に誤ブロック(fail-closed 側)。完全な shell パース不可で、light control として許容。
- **Hook は MCP/deploy/migrate に作動しない** — [ADR-014](./014-loop-engineering-as-discipline.md) 物理層スコープ外。これらは規範 + エージェント model 明示で担保し、Hook が守ると過信しない。
- **agent_id ゲート のサブ編集許可は小穴** — メイン Opus が編集系サブエージェント(`agent_id` あり)を起動した場合、そのサブの編集は許可される。ただし既存の編集系エージェント(`fixer` / `tdd-guide` / `build-error-resolver` 等)は全て `model: sonnet/haiku` 明示済みで実害は限定的。

## 関連

- [ADR-006](./006-hook-error-policy.md) — Hook エラー方針(fail-open 原則)
- [ADR-009](./009-symlink-and-settings-merge.md) — settings マージ規則(model は実行時状態で settings に無い)
- [ADR-014](./014-loop-engineering-as-discipline.md) — 物理層スコープ(Bash・Edit|Write のみ)
- `rules/role-separation.md` — 規範層のロール分離定義
- `rules/loop-safety.md` — 不可逆操作ガード(Hook は git/PR のみ作動)
- `hooks/opus-execution-guard.py` — 実装(74行)
- `skills/loop-engineering/SKILL.md` — STEP4 モデル役割注記
