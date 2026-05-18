#!/usr/bin/env python3
"""PostToolUse(Edit|Write|MultiEdit): 編集後ファイルの console.log を即時警告"""
import json, sys, subprocess

data = json.load(sys.stdin)
path = data.get('tool_input', {}).get('file_path', '')

JS_EXTS = ('.js', '.ts', '.jsx', '.tsx', '.mjs', '.cjs')
if not path or not any(path.endswith(e) for e in JS_EXTS):
    sys.exit(0)

result = subprocess.run(
    ['grep', '-n', r'console\.log', path],
    capture_output=True, text=True
)
if result.stdout:
    print(f'⚠️  console.log を検出: {path}')
    for line in result.stdout.strip().split('\n')[:5]:
        print(f'  {line}')
