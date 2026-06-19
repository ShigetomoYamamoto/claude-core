#!/usr/bin/env python3
"""PreToolUse(Bash): git add による秘匿ファイル(.env/鍵/認証情報)のステージングをブロックする。

`git add --dry-run` で「実際にステージされるファイル」を git 自身に解決させ、秘匿パターンと
照合する。これにより git -C / グローバルオプション / ディレクトリ指定 / -A / . もまとめて
カバーする。

既知の限界(多層防御の他層で補う):
  - git commit -a / -am(add を経ないステージ)は対象外
  - git stash 経由の退避、シンボリックリンクのリンク先は対象外
  - $(...) 等で動的生成されるファイル名は解決しない
  - ファイル名が無害で内容が秘匿のケースは PostToolUse の secret-detection.py が担当
  - 検査不能な例外時は exit 0(開発を止めない方針。ADR-006)
"""
import json, sys, re, subprocess, shlex, fnmatch

SECRET_GLOBS = (
    '.env', '.env.*', '*.env',
    '*.key', '*.pem', '*.secret', '*.p12', '*.pfx', '*.pkcs12',
    '*.keystore', '*.jks', '*.bks', '*.ppk',
    'credentials.*', 'secrets.*', 'secret.*',
    '*service-account*.json', '*-key.json',
    'id_rsa', 'id_dsa', 'id_ecdsa', 'id_ed25519',
    '.npmrc', '.pypirc', '.netrc', '.git-credentials', '.dockercfg',
    'kubeconfig', '*.kubeconfig', '*.tfvars',
    'terraform.tfstate', 'terraform.tfstate.*',
)
# プレースホルダ/サンプル系は誤検知を避けるため明示的に許可する
ALLOW_GLOBS = ('.env.example', '.env.sample', '.env.template', '*.example', '*.sample', '*.dist')


def is_secret(path):
    base = path.rsplit('/', 1)[-1].strip().strip('"').strip("'").lower()
    if not base or any(fnmatch.fnmatch(base, g) for g in ALLOW_GLOBS):
        return False
    if '.env' in base:                       # foo.env / config.env.local 等も秘匿扱い
        return True
    return any(fnmatch.fnmatch(base, g) for g in SECRET_GLOBS)


def staged_files(seg):
    """git add セグメントを --dry-run で実行し、実際にステージ対象となるファイル名を返す。"""
    try:
        tokens = shlex.split(seg)
    except Exception:
        return []
    if 'add' not in tokens:
        return []
    i = tokens.index('add')
    dry = tokens[:i + 1] + ['--dry-run'] + tokens[i + 1:]
    try:
        r = subprocess.run(dry, capture_output=True, text=True, timeout=5)
    except Exception:
        return []
    files = []
    for ln in r.stdout.splitlines():
        m = re.match(r"add '(.+)'$", ln.strip())
        if m:
            files.append(m.group(1))
    return files


try:
    data = json.load(sys.stdin)
    cmd = data.get('tool_input', {}).get('command', '')
    if not cmd or 'git' not in cmd or 'add' not in cmd:
        sys.exit(0)

    hits = set()
    for seg in re.split(r'&&|\|\||;|\n', cmd):
        for f in staged_files(seg.strip()):
            if is_secret(f):
                hits.add(f)

    if hits:
        print('🔴 秘匿ファイルをステージしようとしました:')
        for h in sorted(hits):
            print(f'  - {h}')
        print('これらは .gitignore に追加し、環境変数や秘密管理ツールで管理してください。')
        print('意図的な場合は対象ファイルを個別に指定し直してください。')
        sys.exit(2)

except SystemExit:
    raise
except Exception:
    sys.exit(0)
