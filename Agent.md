# Agent Rules for Novel Translation Studio

This file defines how AI coding agents must work in this project.

## 1. Project Focus

Only work on Novel Translation Studio.

Before coding, read:

- `goal.md`
- `master_plan.md`
- The specific `phase/*.md` file assigned for the current task
- This `Agent.md`
- `working.md`
- Any relevant `Working/*.md` notes from previous agents

Do not expand scope beyond the phase unless the user explicitly asks.

Before starting a phase, check `Working/` to see whether another agent already completed or partially completed that phase. Continue from existing evidence instead of restarting blindly.

## 2. Source of Truth

Use these documents as the project source of truth:

- `goal.md`: why the project exists
- `master_plan.md`: full product and architecture plan
- `phase/*.md`: implementation scope for each phase
- `Agent.md`: agent working rules

Do not modify files inside `Dont_touch/` unless the user explicitly requests it.

## 3. Implementation Discipline

Agents must:

- Follow the current phase document.
- Keep changes scoped to the requested phase.
- Prefer existing project conventions over inventing new ones.
- Keep the app offline-first and single-user.
- Preserve file-based storage assumptions.
- Keep OpenAI-compatible LLM provider assumptions.
- Use English for UI text unless the user asks otherwise.
- Keep dark mode as the primary UI direction.
- Avoid adding cloud sync, collaboration, accounts, auth, or unrelated features.

## 4. Phase Completion Log

After finishing a phase or a meaningful chunk of work, the agent must create a Markdown record in:

```text
Working/*.md
```

Recommended filename:

```text
Working/phase_XX_summary.md
```

If multiple agents work on the same phase, use a suffix:

```text
Working/phase_XX_summary_YYYYMMDD_HHMM.md
```

The `Working/*.md` file is the detailed evidence of work.

It must include:

- Phase/task name
- Date
- Files changed
- What was implemented
- What was tested
- Known issues
- Remaining work
- Important decisions or deviations from the plan

## 5. Root `working.md`

The root `working.md` is only a tiny index.

It must stay extremely short.

Rules:

- Do not write long explanations in root `working.md`.
- Do not paste test logs into root `working.md`.
- Do not delete existing entries unless the user explicitly asks.
- Append one short entry after finishing work.
- Each entry should point to the detailed `Working/*.md` file.

Recommended format:

```md
- YYYY-MM-DD: Phase XX done. Details: `Working/phase_XX_summary.md`.
```

Root `working.md` should answer only:

- What was done?
- Where is the detailed note?

## 6. Testing and Verification

Every coding agent should verify the work before claiming completion.

At minimum, record in the phase summary:

- Commands run
- Tests passed or failed
- Manual checks performed
- Anything that could not be tested

If tests are not available yet, say that clearly.

## 7. Handling Problems

If the agent finds a blocker:

- Do not silently skip it.
- Record it in the relevant `Working/*.md` file.
- Add a short root `working.md` entry pointing to that note.
- Explain whether the blocker is technical, product-scope, missing dependency, unclear spec, or user decision needed.

## 8. Editing Existing Work Logs

`Working/*.md` files are evidence records.

Agents may append corrections, but should not rewrite old evidence unless the user explicitly asks.

If a previous note is wrong, append a correction section:

```md
## Correction

...
```

## 9. Final Response to User

When reporting completion to the user, keep it concise:

- Say what was done.
- Mention tests/checks.
- Point to the detailed `Working/*.md` note if relevant.

Do not dump long logs into chat unless asked.
