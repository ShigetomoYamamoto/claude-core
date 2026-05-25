#!/usr/bin/env python3
"""PreToolUse(Edit|Write|MultiEdit): 保護されたブランチ上でのファイル編集をブロックする。
develop ブランチが存在する（= git-flow 運用中）プロジェクトのみ対象。"""
import json, sys, re, subprocess

try:
    subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'],
                   capture_output=True, check=True, timeout=5)
except Exception:
    sys.exit(0)

try:
    r = subprocess.run(['git', 'branch', '--show-current'],
                       capture_output=True, text=True, timeout=5)
    current = r.stdout.strip()
except Exception:
    sys.exit(0)

PROTECTED = (
    'main', 'master',           # GitHub/Git デフォルトブランチ
    'develop', 'development',   # Git Flow 開発ブランチ
    'staging',                  # ステージング環境
    'release',                  # リリースブランチ
    'production', 'prod',       # 本番環境
    'trunk',                    # Trunk-based development
)
if current not in PROTECTED:
    sys.exit(0)

# main/master 以外の protected branch が存在する場合のみ
# マルチブランチ運用中と判断してブロック
SECONDARY = {'develop', 'development', 'staging', 'release', 'production', 'prod', 'trunk'}
try:
    all_r = subprocess.run(['git', 'branch', '-a'],
                           capture_output=True, text=True, timeout=5)
    existing = set(re.findall(r'\b\w+\b', all_r.stdout))
    if not (SECONDARY & existing):
        sys.exit(0)
except Exception:
    sys.exit(0)

try:
    data = json.load(sys.stdin)
    file_path = (
        data.get('tool_input', {}).get('file_path')
        or data.get('tool_input', {}).get('path', '')
    )
except Exception:
    file_path = ''

print(f'🔴 保護されたブランチ "{current}" 上でファイルを編集しようとしています。')
print(f'  対象ファイル: {file_path}')
print('作業ブランチを作成してから実装を開始してください。')
print('  /create-branch を使用するか:')
print('  git checkout -b <prefix>/<summary>_YYYYMMDD')
sys.exit(2)
