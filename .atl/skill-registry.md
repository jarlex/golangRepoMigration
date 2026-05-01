# Skill Registry

**Delegator use only.** Any agent that launches sub-agents reads this registry to resolve compact rules, then injects them directly into sub-agent prompts. Sub-agents do NOT read this registry or individual SKILL.md files.

See `_shared/skill-resolver.md` for the full resolution protocol.

## User Skills

| Trigger | Skill | Path |
|---------|-------|------|
| When writing Go tests, using teatest, or adding test coverage. | go-testing | /home/jarlex/.config/opencode/skills/go-testing/SKILL.md |
| When creating a GitHub issue, reporting a bug, or requesting a feature. | issue-creation | /home/jarlex/.config/opencode/skills/issue-creation/SKILL.md |
| When creating a pull request, opening a PR, or preparing changes for review. | branch-pr | /home/jarlex/.config/opencode/skills/branch-pr/SKILL.md |
| When user says "judgment day", "judgment-day", "review adversarial", "dual review", "doble review", "juzgar", "que lo juzguen". | judgment-day | /home/jarlex/.config/opencode/skills/judgment-day/SKILL.md |
| When user asks to create a new skill, add agent instructions, or document patterns for AI. | skill-creator | /home/jarlex/.config/opencode/skills/skill-creator/SKILL.md |

## Compact Rules

Pre-digested rules per skill. Delegators copy matching blocks into sub-agent prompts as `## Project Standards (auto-resolved)`.

### go-testing
- Prefer table-driven tests with `t.Run` for multi-case behavior.
- For Bubbletea, test `Model.Update()` transitions directly before full-flow tests.
- Use `teatest.NewTestModel` for interactive TUI flows and key sequences.
- Use golden files in `testdata/` for stable view/render assertions.
- Use `t.TempDir()` for filesystem/system-side effects; avoid global state.
- Cover success and error paths explicitly in assertions.

### issue-creation
- Always use GitHub issue templates; blank issues are disallowed.
- New issues must start with `status:needs-review` (auto-label expected).
- PR work MUST wait for maintainer-applied `status:approved`.
- Route questions to Discussions, not Issues.
- Choose correct template (bug vs feature) and fill required fields completely.
- Check for duplicates before creating new issues.

### branch-pr
- Every PR MUST link an approved issue via `Closes/Fixes/Resolves #N`.
- Use branch format `type/description` matching allowed regex.
- Add exactly one `type:*` label consistent with PR intent.
- Follow conventional commits; no invalid types/scopes.
- Ensure required validation checks (issue reference, approval label, type label, shellcheck) pass.
- Keep PR body complete: summary, changes table, and test plan.

### judgment-day
- Launch two independent blind judges in parallel with identical criteria.
- Synthesize findings by agreement: confirmed, suspect, contradiction.
- Classify warnings as real vs theoretical; theoretical warnings are INFO only.
- Fix only confirmed issues through a separate fix agent, then re-judge.
- After two fix iterations with remaining issues, ask user whether to continue.
- Never mark APPROVED until convergence criteria are met.

### skill-creator
- Create skills only for reusable, non-trivial patterns.
- Use canonical `SKILL.md` frontmatter with name, description+Trigger, license, metadata.
- Keep guidance actionable: critical patterns first, minimal examples.
- Place reusable templates/schemas in `assets/`, local doc pointers in `references/`.
- Follow naming conventions by domain (`technology`, `action-target`, etc.).
- Register new skills in project guidance index when applicable.

## Project Conventions

| File | Path | Notes |
|------|------|-------|
| — | — | No project-level convention files detected in repository root (`agents.md`, `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `GEMINI.md`, `copilot-instructions.md`). |

Read the convention files listed above for project-specific patterns and rules. All referenced paths have been extracted — no need to read index files to discover more.
