#!/usr/bin/env python3
"""PreToolUse(Bash): git の破壊的操作をブロックする"""
import json, sys, re, subprocess

def current_branch():
    try:
        r = subprocess.run(['git', 'branch', '--show-current'], capture_output=True, text=True, timeout=5)
        return r.stdout.strip()
    except Exception:
        return ''

try:
    data = json.load(sys.stdin)
    cmd = data.get('tool_input', {}).get('command', '')

    if not cmd or 'git' not in cmd:
        sys.exit(0)

    PROTECTED = (
        'main', 'master',           # GitHub/Git デフォルトブランチ
        'develop', 'development',   # Git Flow 開発ブランチ
        'staging',                  # ステージング環境
        'release',                  # リリースブランチ
        'production', 'prod',       # 本番環境
        'trunk',                    # Trunk-based development
    )

    # git commit on protected branch
    if re.search(r'\bgit\s+commit\b', cmd):
        branch = current_branch()
        if branch in PROTECTED:
            print(f'🔴 保護されたブランチ "{branch}" 上でコミットしようとしました。')
            print('作業ブランチを作成してから作業してください。')
            print('  /create-branch を使用するか:')
            print('  git checkout -b <prefix>/<summary>_YYYYMMDD')
            sys.exit(2)

    # git push (non-force) on protected branch
    if re.search(r'\bgit\s+push\b', cmd) and not re.search(r'(?:-f\b|--force\b|--force-with-lease\b)', cmd):
        branch = current_branch()
        if branch in PROTECTED:
            print(f'🔴 保護されたブランチ "{branch}" から直接 push しようとしました。')
            print('作業ブランチから PR を作成してください。')
            print('  /create-branch → 実装 → /create-pr の手順で進めてください。')
            sys.exit(2)

    # git push --force / --force-with-lease to protected branch
    push_force = re.search(r'\bgit\s+push\s+.*(?:-f\b|--force\b|--force-with-lease\b)', cmd)
    if push_force:
        for b in PROTECTED:
            if re.search(rf'\b{b}\b', cmd):
                print(f'🔴 git push --force を {b} ブランチに対して実行しようとしました。')
                print('保護されたブランチへの force push は禁止です。')
                sys.exit(2)

    # git reset --hard with unpushed commits
    if re.search(r'\bgit\s+reset\s+.*--hard\b', cmd):
        try:
            r = subprocess.run(
                ['git', 'log', '@{u}..HEAD', '--oneline'],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode == 0 and r.stdout.strip():
                count = len(r.stdout.strip().split('\n'))
                print(f'🔴 未プッシュのコミットが {count} 件あります。git reset --hard で失われます。')
                print(f'未プッシュコミット:\n{r.stdout}')
                sys.exit(2)
        except Exception:
            pass

    # git clean -fd / -df / etc
    if re.search(r'\bgit\s+clean\s+.*-[a-z]*f[a-z]*d|--force.*-d|-d.*--force', cmd):
        print('🔴 git clean -fd は未追跡ファイル・ディレクトリを完全削除します。')
        print('意図したものか確認してから手動で実行してください。')
        sys.exit(2)

    # git checkout . / git restore . (uncommitted changes wipe)
    if re.search(r'\bgit\s+(checkout|restore)\s+\.\s*$', cmd):
        print('🔴 git checkout . / git restore . は未コミットの変更をすべて破棄します。')
        print('意図したものか確認してから手動で実行してください。')
        sys.exit(2)

except SystemExit:
    raise
except Exception:
    sys.exit(0)
