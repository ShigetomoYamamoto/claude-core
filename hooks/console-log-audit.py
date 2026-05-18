#!/usr/bin/env python3
"""Stop: セッション終了前に変更ファイル全体の console.log を一括チェック"""
import subprocess, sys

r1 = subprocess.run(['git', 'diff', '--name-only', 'HEAD'], capture_output=True, text=True)
r2 = subprocess.run(['git', 'diff', '--name-only', '--cached'], capture_output=True, text=True)

JS_EXTS = ('.js', '.ts', '.jsx', '.tsx', '.mjs', '.cjs')
all_files = set((r1.stdout + r2.stdout).strip().split('\n'))
js_files = [f for f in all_files if f and any(f.endswith(e) for e in JS_EXTS)]

found = False
for f in js_files:
    try:
        r = subprocess.run(['grep', '-n', r'console\.log', f], capture_output=True, text=True)
        if r.stdout:
            if not found:
                print('⚠️  console.log が残っています:')
                found = True
            print(f'  {f}:')
            for line in r.stdout.strip().split('\n'):
                print(f'    {line}')
    except Exception:
        pass
