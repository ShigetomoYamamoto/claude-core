#!/usr/bin/env python3
"""night-mode-guard.py の契約テスト(stdlib unittest)。

実行: python3 hooks/test_night_mode_guard.py
本物の ~/.claude/night-mode.json には触れない。毎回一時 HOME を作り、subprocess の HOME に渡す。
"""
import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "night-mode-guard.py")
JST = timezone(timedelta(hours=9))
U = "mcp__9170bb7c-b011-4e4b-b28e-ff8e3d0a2256__"
G = "mcp__22486bf0-da5a-4531-9498-4eb69829e1d8__"
N = "mcp__23c9d278-b2be-45c8-99d9-a995c05f2507__"
C = "mcp__3d5ebf9d-4425-48b5-aac7-25b143a8271e__"
D = "mcp__5824fca4-37b7-46c0-a635-260e1a21d80b__"
S = "mcp__b1abe937-4748-4089-b265-89540e46d24a__"

MCP_BLOCKED = [U + t for t in ("slack_send_message", "slack_send_message_draft", "slack_schedule_message",
                               "slack_create_canvas", "slack_update_canvas", "slack_add_reaction")] + [
    "mcp__plugin_slack-by-salesforce_slack__slack_send_message"] + [
    G + t for t in ("send_message", "create_draft", "reply", "forward", "update_draft", "trash_thread")] + [
    N + t for t in ("notion-create-pages", "notion-update-page", "notion-delete-pages", "notion-move-pages",
                    "notion-create-comment", "notion-duplicate-page", "notion-send-message-to-session",
                    "notion-calendar-create-events")] + [
    "mcp__notion-crien__API-post-page", "mcp__notion-crien__API-patch-page",
    "mcp__notion-crien__API-patch-block-children"] + [
    C + t for t in ("create_event", "update_event", "delete_event", "respond_to_event")] + [
    "mcp__claude_ai_Google_Calendar__create_event"] + [
    D + t for t in ("share_file", "create_file", "update_file", "trash_file")] + [
    S + "update_values", S + "append_values",
    "mcp__d1f970eb-12d3-42a4-95ea-c8992326918f__update_doc",
    "mcp__7e7f3d53-880f-41a9-818c-a7430e4b992d__update_presentation",
    "mcp__plugin_github_github__create_pull_request", "mcp__plugin_github_github__merge_pull_request",
    "mcp__plugin_github_github__push_files", "mcp__plugin_github_github__add_issue_comment",
    "mcp__plugin_github_github__create_or_update_file", "mcp__workspace-mcp-write__modify_sheet_values",
    "mcp__Claude_Browser__navigate", "mcp__Claude_Browser__computer", "mcp__terminal__run_in_terminal",
    "mcp__ccd_pr__set_auto_merge", "mcp__ccd_session__move_to_cloud"]

MCP_ALLOWED = [U + "slack_read_channel", U + "slack_search_public", G + "search_threads", G + "get_thread",
               G + "list_drafts", N + "notion-fetch", N + "notion-search", N + "notion-query-data-sources",
               N + "notion-get-comments", "mcp__notion-crien__API-post-search",
               "mcp__notion-crien__API-get-users", "mcp__notion-crien__API-retrieve-a-page",
               C + "list_events", C + "get_event", D + "read_file_content", S + "get_values",
               "mcp__d1f970eb-12d3-42a4-95ea-c8992326918f__read_doc",
               "mcp__plugin_github_github__get_pull_request", "mcp__plugin_github_github__list_commits",
               "mcp__unityMCP-desktop__manage_editor", "mcp__unityMCP-desktop__run_tests",
               "mcp__unityMCP-desktop__manage_scene", "mcp__ccd_session_mgmt__send_message",
               "mcp__ccd_session_mgmt__list_sessions", "mcp__ccd_turn__update_plan",
               "mcp__Claude_Browser__read_page"]

MARKER_REL = os.path.join(".claude", "night-mode.json")


class Env:
    """一時 HOME。marker=None ならマーカー無し。"""

    def __init__(self, marker=None):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.realpath(self.tmp.name)
        os.makedirs(os.path.join(self.home, ".claude"))
        self.marker = os.path.join(self.home, MARKER_REL)
        if marker is not None:
            with open(self.marker, "w", encoding="utf-8") as f:
                f.write(marker)

    def run(self, tool, tool_input=None):
        payload = {"tool_name": tool, "tool_input": tool_input or {}, "cwd": self.home}
        return subprocess.run(["python3", HOOK], input=json.dumps(payload), capture_output=True,
                              text=True, env={**os.environ, "HOME": self.home})

    def close(self):
        self.tmp.cleanup()


def marker_json(delta_hours, **extra):
    until = (datetime.now(JST) + timedelta(hours=delta_hours)).isoformat()
    return json.dumps({"version": 1, "until": until, **extra})


class NightModeGuardTest(unittest.TestCase):
    def env(self, marker):
        e = Env(marker)
        self.addCleanup(e.close)
        return e

    def test_no_marker_allows_everything(self):
        e = self.env(None)
        cases = [("Bash", {"command": "git push"}), ("Edit", {"file_path": e.marker}),
                 ("mcp__x__slack_send_message", {}), ("Read", {})]
        for tool, ti in cases:
            r = e.run(tool, ti)
            self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""), tool)

    def test_expired_marker_allows(self):
        e = self.env(marker_json(-1))
        self.assertEqual(e.run("Bash", {"command": "git push"}).returncode, 0)

    def test_until_just_past_is_off_and_future_is_on(self):
        self.assertEqual(self.env(marker_json(-0.001)).run("Bash", {"command": "git push"}).returncode, 0)
        self.assertEqual(self.env(marker_json(0.5)).run("Bash", {"command": "git push"}).returncode, 2)

    def test_zulu_until_is_understood(self):
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.assertEqual(self.env(json.dumps({"until": past})).run("Bash", {"command": "git push"}).returncode, 0)

    def test_fail_closed_markers(self):
        naive = (datetime.now() - timedelta(hours=5)).replace(microsecond=0).isoformat()
        bad = ["not json", "", "[]", "null", "{}", json.dumps({"until": 5}), json.dumps({"until": "tomorrow"}),
               json.dumps({"until": naive}), json.dumps({"version": 1, "active": False})]
        for text in bad:
            r = self.env(text).run("Bash", {"command": "git push"})
            self.assertEqual(r.returncode, 2, text)

    def test_unreadable_marker_is_on(self):
        e = self.env(None)
        os.mkdir(e.marker)  # ファイルではなくディレクトリ → 読めない
        self.assertEqual(e.run("Bash", {"command": "git push"}).returncode, 2)

    def test_dangling_symlink_marker_is_on(self):
        e = self.env(None)
        os.symlink(os.path.join(e.home, "nowhere"), e.marker)
        self.assertEqual(e.run("mcp__x__slack_send_message").returncode, 2)

    def test_message_contents(self):
        e = self.env(marker_json(3))
        r = e.run("Bash", {"command": "git push"})
        for word in ("夜間モード", "git push", e.marker, "until", "削除", "workops night end"):
            self.assertIn(word, r.stderr)

    def test_invalid_stdin_while_on_blocks(self):
        e = self.env(marker_json(3))
        r = subprocess.run(["python3", HOOK], input="{oops", capture_output=True, text=True,
                           env={**os.environ, "HOME": e.home})
        self.assertEqual(r.returncode, 2)

    def test_other_tools_allowed_while_on(self):
        e = self.env(marker_json(3))
        for tool in ("Read", "Grep", "Glob", "Agent", "WebFetch"):
            self.assertEqual(e.run(tool, {"file_path": e.marker}).returncode, 0, tool)

    def test_mcp_tables(self):
        e = self.env(marker_json(3))
        for name in MCP_BLOCKED:
            self.assertEqual(e.run(name).returncode, 2, name)
        self.assertEqual(e.run("mcp__ccd_session__start_session", {"target": "cloud"}).returncode, 2)
        self.assertEqual(e.run("mcp__ccd_session__start_session", {"target": "ssh"}).returncode, 2)
        for name in MCP_ALLOWED:
            self.assertEqual(e.run(name).returncode, 0, name)
        self.assertEqual(e.run("mcp__ccd_session__start_session", {}).returncode, 0)
        self.assertEqual(e.run("mcp__ccd_session__start_session", {"target": "local"}).returncode, 0)

    def test_bash_blocked(self):
        e = self.env(marker_json(3))
        blocked = ["git push", "git -C /x push origin HEAD", "cd x && git push", 'g"it" push', "\\git push",
                   "gh pr create --base develop", "gh pr merge 3", "gh pr review 3 --approve",
                   "gh pr comment 3 -b x", "gh issue create", "gh release create v1",
                   "gh api repos/o/r/issues -f title=x", "gh api -X POST repos/o/r/pulls",
                   "rm ~/.claude/night-mode.json", "pnpm workops night end", "echo {} > ~/.claude/settings.json",
                   "git send-email x.patch", "ls; git push", "(git push)", "echo a | git push",
                   "git push 'origin'", "/usr/bin/git push", "git -c x=y push", "sudo git push",
                   "env A=1 git push", "bash -c 'git push'", "sh -c \"cd x && git push\"", "eval 'git push'",
                   "gh api repos/o/r --method=PATCH", "gh api repos/o/r -XDELETE", "gh api x --input f.json",
                   "gh api x -F a=b", "gh api x --field a=b", "gh pr checkout 3", "gh pr",
                   "echo $(git push)", "echo \"$(git push)\"", "cat .claude/hooks/x.py",
                   "vi .claude/settings.local.json", "n\"ight\"-mode", "pnpm workops night start",
                   "python3 -c \"import subprocess; subprocess.run(['git','push'])\""]
        for cmd in blocked:
            self.assertEqual(e.run("Bash", {"command": cmd}).returncode, 2, cmd)

    def test_bash_allowed(self):
        e = self.env(marker_json(3))
        allowed = ["git commit -m x", "git status", "git checkout -b feat/x", "gh pr view 3", "gh pr checks 3",
                   "gh api repos/o/r/pulls", "pnpm test", "ls", "git log --oneline", "git -C /x status",
                   "git diff && git add a", "git worktree add ../x -b y", "gh api -X GET repos/o/r",
                   "gh search issues foo", "gh run watch 5", "gh release download v1", "gh auth status",
                   "git commit -m \"fix; git push は使わない\"", "echo 'git push'", "gh -R o/r pr view 3",
                   "git branch --list push*", "gh repo clone o/r", "gh pr list --json number"]
        for cmd in allowed:
            r = e.run("Bash", {"command": cmd})
            self.assertEqual(r.returncode, 0, f"{cmd}: {r.stderr}")

    def test_edit_write_tables(self):
        e = self.env(marker_json(3))
        protected = [e.marker, os.path.join(e.home, ".claude", "settings.json"),
                     "/repo/.claude/settings.local.json", os.path.join(e.home, ".claude", "hooks", "x.py")]
        for tool in ("Edit", "Write", "MultiEdit"):
            for path in protected:
                self.assertEqual(e.run(tool, {"file_path": path}).returncode, 2, f"{tool} {path}")
            self.assertEqual(e.run(tool, {"file_path": "/repo/src/a.ts"}).returncode, 0)
        self.assertEqual(e.run("NotebookEdit", {"notebook_path": e.marker}).returncode, 2)
        self.assertEqual(e.run("NotebookEdit", {"notebook_path": "/repo/a.ipynb"}).returncode, 0)

    def test_tilde_symlink_and_relative_marker_paths_blocked(self):
        e = self.env(marker_json(3))
        link = os.path.join(e.home, "link.json")
        os.symlink(e.marker, link)
        self.assertEqual(e.run("Write", {"file_path": link}).returncode, 2)
        self.assertEqual(e.run("Write", {"file_path": MARKER_REL}).returncode, 2)  # cwd=HOME からの相対
        self.assertEqual(e.run("Write", {"file_path": "~/.claude/settings.json"}).returncode, 2)


if __name__ == "__main__":
    unittest.main()
