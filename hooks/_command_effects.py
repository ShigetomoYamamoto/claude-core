#!/usr/bin/env python3
"""コマンド文字列から「効果」を推し量るための共有ヘルパ(ADR-028)。

これは検出網であってセキュリティ境界ではない。シェル/インタプリタへ渡された
任意コードの効果を文字列から確定することは原理的にできない。ここが扱うのは
「インタプリタにインラインコードを渡す呼び出し形式」という、列挙可能で
ペイロードの中身に依存しない部分だけ。何を危険とみなすかの判断は各 hook が持つ
(mass-delete-blocker は削除 API、main-loop-execution-guard は書き込み+削除 API)。

各 hook はこのモジュールを try/except で読み込み、欠けても従来どおり動くこと。
"""
import re

# インラインコードを渡されうるインタプリタ。シェルは別扱い(_SHELL)。
_INTERP = r'(?:python[\d.]*|node|nodejs|deno|bun|perl|ruby|php|osascript|Rscript)'
_SHELL = r'(?:bash|sh|zsh|dash|ksh)'

# `python3 -c '...'` / `node -e '...'` / `perl -e ...` / `php -r ...`
_INLINE_FLAG = re.compile(rf'\b{_INTERP}\b[^\n;|&]*?\s-(?:c|e|r|-eval|-exec)\b')
# `python3 - <<EOF` / `python3 <<'PY'` — ヒアドキュメント/標準入力経由
_HEREDOC = re.compile(rf'\b{_INTERP}\b[^\n;|&]*?<<-?\s*[\'"]?\w+')
# `bash -c "..."` / `sh -c '...'` — クォート内に隠れたシェルコマンド
_INLINE_SHELL = re.compile(rf'\b{_SHELL}\b[^\n;|&]*?\s-[a-z]*c\b')

# 既知の削除 API(Python / Node / Perl / Ruby / Rust 等)。網羅ではない。
DELETE_APIS = re.compile(
    r'\bos\.(?:remove|unlink|rmdir|removedirs)\s*\('
    r'|\bshutil\.rmtree\s*\('
    r'|\bunlink\s*\('
    r'|\bfs\.(?:rm|rmSync|rmdir|rmdirSync|unlink|unlinkSync)\s*\('
    r'|\bFileUtils\.(?:rm|rm_r|rm_rf)\b'
    r'|\bFile\.delete\b'
    r'|\bremove_dir_all\s*\('
)

# 既知の書き込み API。stdout/stderr への write は副作用がないため除外する。
WRITE_APIS = re.compile(
    r'''\bopen\s*\([^)]*['"][wax]'''
    r'|(?<!stdout)(?<!stderr)\.write(?:_text|_bytes|lines)?\s*\('
    r'|\bfs\.(?:append|copy|create|mkdir|rename|write)\w*\s*\('
    r'|\bos\.(?:mkdir|makedirs|rename|replace)\s*\('
    r'|\bshutil\.(?:copy\w*|move)\s*\('
)


def has_inline_code(cmd):
    """インタプリタにインラインコード/ヒアドキュメントを渡す呼び出しを含むか。"""
    return bool(_INLINE_FLAG.search(cmd) or _HEREDOC.search(cmd))


def has_inline_shell(cmd):
    """`sh -c` 等、クォート内にシェルコマンドを隠す呼び出しを含むか。"""
    return bool(_INLINE_SHELL.search(cmd))


def unquote_all(cmd):
    """クォート記号だけを空白に置換する(中身は残す)。クォート内に隠れた語を素の解析に載せるため。"""
    return cmd.replace('"', ' ').replace("'", ' ')
