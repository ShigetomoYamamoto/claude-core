#!/usr/bin/env python3
"""Concrete entry point: install this repo's claude-core pack.

Thin wiring only -- see installer.py for all install/update/uninstall/verify
logic. This pack is "global": it installs into ~/.claude by default (override
with --target, mainly for tests).
"""
from pathlib import Path
import sys

from installer import Pack, main

PACK = Pack(
    name="claude-core",
    kind="global",
    repo_root=Path(__file__).resolve().parent,
    managed_paths=["rules", "hooks", "skills"],
    settings_fragment="settings-fragment.json",
    other_domain_manifests=[],
)

if __name__ == "__main__":
    sys.exit(main(PACK, sys.argv[1:]))
