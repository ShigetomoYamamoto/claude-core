#!/usr/bin/env python3
"""PreToolUse(Bash): git の破壊的操作をブロックする"""
import json, sys, re, subprocess

try:
    data = json.load(sys.stdin)
    cmd = data.get('tool_input', {}).get('command', '')

    if not cmd or 'git' not in cmd:
        sys.exit(0)

    PROTECTED = ('main', 'master', 'develop')

    # git push --force / --force-with-lease to protected branch
    push_force = re.search(r'\bgit\s+push\s+.*(?:-f\b|--force\b|--force-with-lease\b)', cmd)
    if push_force:
        for b in PROTECTED:
            if re.search(rf'\b{b}\b', cmd):
                print(f'🔴 git push --force を {b} ブランチに対して実行しようとしました。')
                print('保護されたブランチ（main/master/develop）への force push は禁止です。')
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
