#!/usr/bin/env python3
"""PreToolUse(Bash): git の破壊的操作をブロックする"""
import json, sys, re, subprocess

def _strip_quotes(s):
    return s.strip('\'"')

def resolve_git_dir(cmd):
    """cmd 文字列から「git が実際に走るディレクトリ」を推定する。
    (1) `git -C <dir>` があればその <dir>。
    (2) 無ければ、最初の git 実行箇所より前に現れる最後の `cd <dir>`。
    (3) どちらも無ければ None（呼び出し側はプロセス cwd にフォールバックする）。
    push 先ブランチの評価は行わない（スコープ外）。「保護ブランチ上に居るか」を
    評価する場所を cwd から正しいディレクトリへ正すだけ。"""
    m = re.search(r'\bgit\s+-C\s+(\S+)', cmd)
    if m:
        return _strip_quotes(m.group(1))

    invocation = re.search(r'(?:^|&&|\|\||;|\n)\s*(?:\S+\s+)*(git\s+\S+)', cmd, re.MULTILINE)
    if not invocation:
        return None

    prefix = cmd[:invocation.start(1)]
    cd_matches = list(re.finditer(r'\bcd\s+(\S+)', prefix))
    if not cd_matches:
        return None
    return _strip_quotes(cd_matches[-1].group(1))

def current_branch(cmd=''):
    """cmd から推定した実行ディレクトリ（無ければプロセス cwd）でカレントブランチを返す。
    判定不能・git 失敗時は空文字を返し、PROTECTED 非該当＝許可という従来挙動を保つ。"""
    git_dir = resolve_git_dir(cmd) if cmd else None
    try:
        base = ['git']
        if git_dir:
            base += ['-C', git_dir]
        base += ['branch', '--show-current']
        r = subprocess.run(base, capture_output=True, text=True, timeout=5)
        return r.stdout.strip()
    except Exception:
        return ''

def is_git_invocation(cmd, subcmd):
    """git <subcmd> がシェル演算子の直後か行頭にある（実際に実行される）か判定する。
    grep/echo/python -c 等の引数内に含まれる場合は除外する。`git -C <dir> <subcmd>`
    のように git と subcmd の間に -C <dir> が挟まる形も subcmd の実行として認識する。"""
    pattern = rf'(?:^|&&|\|\||;|\n)\s*(?:\S+\s+)*git\s+(?:-C\s+\S+\s+)?{re.escape(subcmd)}\b'
    return bool(re.search(pattern, cmd, re.MULTILINE))

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
    if is_git_invocation(cmd, 'commit'):
        branch = current_branch(cmd)
        if branch in PROTECTED:
            print(f'🔴 保護されたブランチ "{branch}" 上でコミットしようとしました。')
            print('作業ブランチを作成してから作業してください。')
            print('  /create-branch を使用するか:')
            print('  git checkout -b <prefix>/<summary>_YYYYMMDD')
            sys.exit(2)

    # git push (non-force) on protected branch
    if is_git_invocation(cmd, 'push') and not re.search(r'(?:-f\b|--force\b|--force-with-lease\b)', cmd):
        branch = current_branch(cmd)
        if branch in PROTECTED:
            # ブランチ削除系 push（--delete / -d / コロン refspec ":branch"）は、
            # 削除対象が保護ブランチでなければ許可する。マージ済みブランチの掃除を
            # 保護ブランチ上からでも通すための例外（誤検知の解消）。非保護ブランチの
            # 削除は元々作業ブランチ上では許可されており、ここは挙動を一貫させるだけ。
            is_delete = bool(re.search(r'--delete\b|(?:^|\s)-d\b|\s:\S', cmd))
            if is_delete:
                if any(re.search(rf'\b{re.escape(b)}\b', cmd) for b in PROTECTED):
                    print('🔴 保護されたブランチを削除しようとしました。')
                    print('保護ブランチ（main / master / develop 等）の削除は禁止です。')
                    sys.exit(2)
                sys.exit(0)  # 非保護ブランチの削除は許可
            print(f'🔴 保護されたブランチ "{branch}" から直接 push しようとしました。')
            print('作業ブランチから PR を作成してください。')
            print('  /create-branch → 実装 → /create-pr の手順で進めてください。')
            sys.exit(2)

    # git push --force / --force-with-lease to protected branch
    push_force = re.search(r'(?:^|&&|\|\||;|\n)\s*(?:\S+\s+)*git\s+push\s+.*(?:-f\b|--force\b|--force-with-lease\b)', cmd, re.MULTILINE)
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
