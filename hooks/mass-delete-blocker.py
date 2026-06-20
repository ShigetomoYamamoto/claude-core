#!/usr/bin/env python3
"""PreToolUse(Bash): ファイル大量削除・rm -rf を検知し、実行前に人間へ諾否を確認する。

二層モデル(ADR-014 / loop-safety「物理層」)— 不可逆操作の最終判断は人間(不変条件4):
- ルート / HOME / $HOME の rm -rf は決定的ブロック(exit 2)= 問答無用の遮断(サーキットブレーカ)。
- それ以外の rm -rf、およびワイルドカード大量削除(THRESHOLD 件以上)は
  permissionDecision="ask" を返し、実行前に人間へ確認プロンプトを出す(警告のまま素通りさせない)。
- ask は default/auto/acceptEdits/plan/bypass では確認を強制。人間不在の文脈(dontAsk / 自走ヘッドレス)
  では deny 扱いになり不可逆操作は止まる(fail-closed = 人間がいなければ不可逆は実行しない、で正しい)。
git 操作の不可逆ブロックは git-destructive-blocker.py が担う。
"""
import json, sys, re, glob

THRESHOLD = 10  # この件数以上のワイルドカード削除で確認を促す


def ask(reason):
    """実行前に人間へ確認プロンプトを出す(PreToolUse の permissionDecision=ask)。"""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


try:
    data = json.load(sys.stdin)
    cmd = data.get('tool_input', {}).get('command', '')

    if not cmd:
        sys.exit(0)

    # rm -rf / rm -fr / rm -r -f を検知
    if re.search(r'\brm\s+.*-[a-z]*r[a-z]*f|-[a-z]*f[a-z]*r', cmd):
        # 危険なターゲット（/, ~, $HOME など）= サーキットブレーカ。確認させず即ブロック
        if re.search(r'\brm\s+.*(?:\s|=)(/|~|\$HOME)(\s|/|$)', cmd):
            print('🔴 rm -rf でルート / ホームディレクトリを削除しようとしました。', file=sys.stderr)
            print(f'コマンド: {cmd}', file=sys.stderr)
            sys.exit(2)

        # それ以外の rm -rf は不可逆なので、実行前に人間へ確認
        ask(f'rm -rf を検出しました（削除は取り消せません）。実行してよいか確認してください。\nコマンド: {cmd}')

    # rm + ワイルドカードで大量削除の可能性
    m = re.search(r'\brm\s+(?!-).*?([^\s]*\*[^\s]*)', cmd)
    if m:
        pattern = m.group(1)
        try:
            matches = glob.glob(pattern, recursive=True)
            if len(matches) >= THRESHOLD:
                sample = '\n'.join(f'  - {f}' for f in matches[:10])
                ask(
                    f'rm のワイルドカード削除: {len(matches)} 件が対象です（取り消せません）。'
                    f'実行してよいか確認してください。\nパターン: {pattern}\n最初の10件:\n{sample}'
                )
        except Exception:
            pass

except SystemExit:
    raise
except Exception:
    sys.exit(0)
