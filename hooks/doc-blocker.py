#!/usr/bin/env python3
"""PreToolUse(Write): 不要な .md / .txt ファイルの自動生成をブロックする

CLAUDE_DOC_BLOCKER_ALLOWED_PATHS(":" 区切りの絶対パス prefix、~ 展開可)配下は
コーディングプロジェクト外の個人用途(例: ノートアプリの vault)とみなし対象外にする。
このリポジトリはドメイン中立の正本のため、具体的な vault パスは各利用者の
settings.json の env に設定する(このファイルにはハードコードしない)。
"""
import json, sys, os

data = json.load(sys.stdin)
path = data.get('tool_input', {}).get('file_path', '')

if not path.endswith(('.md', '.txt')):
    sys.exit(0)

if os.path.exists(path):
    sys.exit(0)  # 既存ファイルの編集は許可

abspath = os.path.abspath(os.path.expanduser(path))
for prefix in os.environ.get('CLAUDE_DOC_BLOCKER_ALLOWED_PATHS', '').split(':'):
    prefix = prefix.strip()
    if not prefix:
        continue
    prefix = os.path.abspath(os.path.expanduser(prefix))
    if abspath == prefix or abspath.startswith(prefix + os.sep):
        sys.exit(0)

basename = os.path.basename(path)
parts = path.split('/')

ALLOWED_NAMES = {'CLAUDE.md', 'ONBOARDING.md', 'CHANGELOG.md', 'MEMORY.md', 'SKILL.md', 'README.md'}
ALLOWED_DIRS  = {'.claude', 'docs', '.github', 'memory', 'skills', 'commands', 'agents', 'rules', 'tmp'}

if basename in ALLOWED_NAMES:
    sys.exit(0)

for part in parts[:-1]:
    if part in ALLOWED_DIRS:
        sys.exit(0)

print(f'[doc-blocker] ドキュメントファイルの自動生成をブロックしました: {path}')
print('ユーザーから明示的に指示された場合のみ作成できます。')
sys.exit(2)
