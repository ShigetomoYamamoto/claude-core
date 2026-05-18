#!/usr/bin/env python3
"""PreToolUse(Write): 不要な .md / .txt ファイルの自動生成をブロックする"""
import json, sys, os

data = json.load(sys.stdin)
path = data.get('tool_input', {}).get('file_path', '')

if not path.endswith(('.md', '.txt')):
    sys.exit(0)

if os.path.exists(path):
    sys.exit(0)  # 既存ファイルの編集は許可

basename = os.path.basename(path)
parts = path.replace('\\', '/').split('/')

ALLOWED_NAMES = {'CLAUDE.md', 'ONBOARDING.md', 'CHANGELOG.md', 'MEMORY.md'}
ALLOWED_DIRS  = {'.claude', 'docs', '.github', 'memory'}

if basename in ALLOWED_NAMES:
    sys.exit(0)

for part in parts[:-1]:
    if part in ALLOWED_DIRS:
        sys.exit(0)

print(f'[doc-blocker] ドキュメントファイルの自動生成をブロックしました: {path}')
print('ユーザーから明示的に指示された場合のみ作成できます。')
sys.exit(2)
