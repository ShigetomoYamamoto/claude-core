#!/usr/bin/env python3
"""PreToolUse(Bash): 大量ファイル削除・rm -rf を検知して確認・ブロックする"""
import json, sys, re, subprocess, glob

THRESHOLD = 10  # この件数以上の削除で警告

try:
    data = json.load(sys.stdin)
    cmd = data.get('tool_input', {}).get('command', '')

    if not cmd:
        sys.exit(0)

    # rm -rf / rm -fr / rm -r -f を検知
    if re.search(r'\brm\s+.*-[a-z]*r[a-z]*f|-[a-z]*f[a-z]*r', cmd):
        # 危険なターゲット（/, ~, $HOME など）
        if re.search(r'\brm\s+.*(?:\s|=)(/|~|\$HOME)(\s|/|$)', cmd):
            print('🔴 rm -rf でルート / ホームディレクトリを削除しようとしました。')
            print(f'コマンド: {cmd}')
            sys.exit(2)

        print('⚠️  rm -rf を検出しました。削除対象を確認してください。')
        print(f'コマンド: {cmd}')
        # rm -rf 自体はブロックしない（warning のみ）
        sys.exit(0)

    # rm + ワイルドカードで大量削除の可能性
    m = re.search(r'\brm\s+(?!-).*?([^\s]*\*[^\s]*)', cmd)
    if m:
        pattern = m.group(1)
        try:
            matches = glob.glob(pattern, recursive=True)
            if len(matches) >= THRESHOLD:
                print(f'⚠️  rm でのワイルドカード削除: {len(matches)} 件のファイルが対象です。')
                print(f'パターン: {pattern}')
                print('意図したものか確認してください（最初の 10 件）:')
                for f in matches[:10]:
                    print(f'  - {f}')
                # warning のみ
        except Exception:
            pass

except SystemExit:
    raise
except Exception:
    sys.exit(0)
