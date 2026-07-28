#!/usr/bin/env python3
"""PreToolUse(Write): 想定外の .md / .txt ファイルの自動生成を実行前に人間へ確認する

allowlist(ALLOWED_NAMES / ALLOWED_DIRS)は「Claude が自発的に作りがちな典型パターン」の
近似でしかなく、「ユーザーが明示的に指示したか」は判定できない。そのため一致しない場合も
決定的ブロック(exit 2)ではなく permissionDecision="ask" とし、人間が明示指示済みなら
その場で許可できるようにする(default/auto/acceptEdits/plan/bypass で確認を強制。
人間不在の dontAsk/自走ヘッドレスでは deny 扱いで止まる — mass-delete-blocker.py と同じ規約)。

CLAUDE_DOC_BLOCKER_ALLOWED_PATHS(":" 区切りの絶対パス prefix、~ 展開可)配下は
コーディングプロジェクト外の個人用途(例: ノートアプリの vault)とみなし確認なしで許可する。
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

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "ask",
        "permissionDecisionReason": (
            f'[doc-blocker] 想定外のドキュメントファイル作成です: {path}\n'
            'ユーザーから明示的に指示されたものであれば許可してください。'
        ),
    }
}))
sys.exit(0)
