#!/usr/bin/env python3
"""PreToolUse(Bash): gh pr create の base が develop 以外ならブロックする"""
import json, sys, re

try:
    data = json.load(sys.stdin)
    cmd = data.get('tool_input', {}).get('command', '')

    if not cmd or 'gh pr create' not in cmd:
        sys.exit(0)

    # --base <branch> を抽出
    m = re.search(r'--base[=\s]+([^\s]+)', cmd)
    if m:
        base = m.group(1).strip("'\"")
        if base != 'develop':
            print(f'🔴 PR の base が "{base}" になっています。base は "develop" のみ許可されます。')
            print('main / master への PR は禁止です。')
            sys.exit(2)
    else:
        # --base 指定なし（デフォルトブランチに向く可能性）
        print('⚠️  gh pr create に --base が指定されていません。')
        print('明示的に --base develop を指定してください。')
        sys.exit(2)

except SystemExit:
    raise
except Exception:
    sys.exit(0)
