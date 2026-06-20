#!/usr/bin/env python3
"""PostToolUse(Edit|Write|MultiEdit): ハードコードされたシークレットを検出して警告。

二層モデル(ADR-014 / loop-safety「物理層」): これは「検出/警告層」(exit 2 なし=止めない)。
ステージ時の決定的ブロックは git-add-secret-blocker.py が担う(git add --dry-run で実ステージ対象を検査)。
commit -a / stash など add を経由しない経路は、この検出層が書込後に後追いで拾う。
"""
import json, sys, re

data = json.load(sys.stdin)
path = data.get('tool_input', {}).get('file_path', '')

EXTS = ('.js', '.ts', '.jsx', '.tsx', '.mjs', '.py', '.json', '.yaml', '.yml', '.env')
if not path or not any(path.endswith(e) for e in EXTS):
    sys.exit(0)

# .env.example は除外（プレースホルダーが含まれるため）
if '.env.example' in path or path.endswith('.example'):
    sys.exit(0)

try:
    content = open(path).read()
except Exception:
    sys.exit(0)

PATTERNS = [
    (r'sk-[a-zA-Z0-9]{20,}',                                    'OpenAI/Anthropic APIキー'),
    (r'(?:API_KEY|APIKEY)\s*=\s*["\'][^\s"\']{10,}["\']',       'APIキー'),
    (r'(?:SECRET_KEY|SECRET)\s*=\s*["\'][^\s"\']{10,}["\']',    'シークレット'),
    (r'(?:PASSWORD|PASSWD)\s*=\s*["\'][^\s"\']{5,}["\']',       'パスワード'),
    (r'ghp_[a-zA-Z0-9]{36}',                                     'GitHub PAT'),
    (r'eyJ[a-zA-Z0-9_-]{50,}\.[a-zA-Z0-9_-]{20,}',             'JWT Token'),
]

found = [label for pattern, label in PATTERNS if re.search(pattern, content)]
if found:
    print(f'🔴 シークレット検出 [{path}]: {", ".join(found)}')
    print('環境変数 (.env) または秘密管理ツールに移動してください。')
