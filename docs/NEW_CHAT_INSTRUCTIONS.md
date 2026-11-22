# New Chat Handoff Instructions — HTP-1 Integration

Use this document when starting a new ChatGPT conversation about this repository. Its purpose is to make the project context and working rules easy to transfer without pasting the entire project history.

## Canonical project context

Repository: https://github.com/joemacjr92/uc-intg-monoprice-htp1

**Before doing project work, read the complete [PROJECT_HANDOFF.md](PROJECT_HANDOFF.md) on the `tests-and-docs` branch.** It is the canonical source for the approved roadmap, branch strategy, development constraints, and project-specific decisions.

The live GitHub repository is authoritative for current implementation status. The handoff document records agreed intent and context; it must not be treated as proof that a task, test, or phase is complete.

## Critical product and device-context distinction

This repository is the **Unfolded Circle integration for the Monoprice HTP-1**. Keep the Unfolded Circle platform/integration context separate from the user's Couch device and any Couch-related project or operating-environment context. The integration target is the HTP-1; the platform is Unfolded Circle. Do not conflate device identities or project environments. If a role or device identity is uncertain, verify it or ask rather than infer from prior project context.

## Copy-and-paste prompt for a new chat

```text
We're continuing development of my Monoprice HTP-1 integration.

Repository:
https://github.com/joemacjr92/uc-intg-monoprice-htp1

Start by reading the complete project handoff:
https://github.com/joemacjr92/uc-intg-monoprice-htp1/blob/tests-and-docs/docs/PROJECT_HANDOFF.md

Before proposing or making changes:

1. Read and follow PROJECT_HANDOFF.md, including the Phase 0–6 roadmap, branch strategy, and scope restrictions.
2. Inspect the live GitHub state relevant to this work: branches and their heads, recent commits, open PRs, CI/check results, and the relevant source and test files.
3. Establish what is actually complete from repository and test evidence. Do not infer completion from the roadmap or an earlier chat summary.
4. Identify the current phase and the next unfinished task.
5. Summarize the verified status and recommend the next task. Wait for my agreement before modifying code.

Important project rules:

- This is the Unfolded Circle integration for the Monoprice HTP-1. Keep it distinct from the separate Couch device/project context and from Fire TV development.
- Keep the fork's main branch aligned with Mase's upstream; do not develop independent production changes on main.
- Use tests-and-docs for tests, fixtures, documentation, handoff material, and QA-only workflows.
- Make production changes on focused feature/* branches.
- Keep unrelated hosted BEQ catalogue work separate from the approved HTP-1 feature roadmap.
- Preserve existing behavior unless an approved task explicitly requires a correction.
- Keep scope tight; do not add deferred features or reinterpret requirements without asking.
- Add regression tests for corrections and distinguish unit tests, CI, remote connectivity, and real HTP-1 hardware validation.
- Use only the user's established private remote-access path for remote testing. Do not record private endpoints, addresses, hostnames, tunnel details, or proxy topology in repository documentation. Do not enable public port forwarding or change the access setup without approval.
- Do not merge, publish, release, deploy, or push upstream without my explicit approval.
- Keep PROJECT_HANDOFF.md updated on tests-and-docs when I approve material plan or status changes. Do not include QA/handoff files in production PRs.

First response: give me the verified project status, current phase, completed work with evidence, and the next planned task. Do not start editing until we agree.
```

## Rules for maintaining this handoff

- Keep this file and `docs/PROJECT_HANDOFF.md` on `tests-and-docs`.
- Do not copy either file into production feature branches or upstream PRs.
- Update the canonical project handoff when approved decisions, phase scope, branch rules, or verified status materially change.
- Keep this file focused on how to start and conduct a new chat. Put detailed technical decisions and roadmap content in `PROJECT_HANDOFF.md` rather than duplicating them here.
- If this file and `PROJECT_HANDOFF.md` ever conflict, follow `PROJECT_HANDOFF.md` and correct this file.
