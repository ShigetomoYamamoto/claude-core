# Answer-Only Mode (Read-Only Until Asked)

Until the user explicitly asks for a change, stay read-only: investigate, answer,
and propose — but do NOT edit/create files, run mutating commands, or commit.

## What counts as an explicit request

- "implement X" / "fix X" / "create X" / 「作って」「直して」「実装して」 — a clear
  instruction to change code or files. From then on you may edit **within that scope**.
- A question ("how does X work?" / 「なぜ X?」) or a vague musing is NOT a request to change.

## While in answer-only

- Read / Grep / Glob / search freely.
- Surface findings and propose concrete changes, but wait for the go-ahead before editing.
- Changes beyond what was asked go back out as a proposal — never silent out-of-scope edits.

## Relation

- A skill or command the user invoked IS an explicit request for its stated purpose;
  acting within that scope does not violate answer-only (see `skills/loop-engineering/SKILL.md`).
- Irreversible / outward-facing steps (push, deploy, delete, external send) still need
  confirmation even after a request — see `rules/loop-safety.md`.
