# CLAUDE.md — Trading Dragonsword

This file is the authoritative guide for AI assistants (Claude Code and similar tools) working in this repository. Read it fully before making any changes.

---

## Project Overview

**Trading Dragonsword** is a trading application (codebase under active development). This CLAUDE.md was created when the repository was first initialized and should be updated as the project grows.

- **Repository**: `alexyudragonsword-collab/trading_dragonsword`
- **Primary branch**: `main`
- **Development branch convention**: `claude/<description>-<id>` for AI-driven work

---

## Repository Status

> This repository is in its initial state. No source files, dependencies, or infrastructure exist yet. The conventions below are baseline rules to follow from the first commit onward.

Once code is added, update the following sections:
- [ ] Tech stack / language
- [ ] Directory structure
- [ ] Build and test commands
- [ ] Environment variables
- [ ] Deployment workflow

---

## Development Branch

All AI-assisted changes must be committed to the designated feature branch and pushed before the session ends. Never push directly to `main` without explicit user approval.

```
git checkout -b claude/<description>-<id>
git push -u origin claude/<description>-<id>
```

---

## Git Conventions

- Commit messages should be concise and describe *why*, not just *what*.
- Never amend published commits; create new ones instead.
- Never skip pre-commit hooks (`--no-verify`) unless the user explicitly requests it.
- Never force-push to `main`.
- Stage specific files — avoid `git add -A` or `git add .` to prevent accidentally committing secrets.
- Do NOT create a pull request unless the user explicitly asks for one.

---

## Code Style (defaults until overridden)

- Prefer editing existing files over creating new ones.
- Do not add features, abstractions, or error handling beyond what the task requires.
- Write no comments by default. Only add a comment when the *why* is non-obvious.
- No docstrings unless the project language/framework convention requires them.
- Keep functions small and single-purpose.
- No backwards-compatibility shims for code that is simply being removed.

---

## Security

- Never commit secrets, API keys, tokens, or credentials. Use environment variables.
- Validate input only at system boundaries (user input, external APIs); trust internal guarantees.
- Avoid introducing OWASP Top 10 vulnerabilities: SQL injection, XSS, command injection, etc.
- If insecure code is introduced accidentally, fix it immediately before continuing.

---

## Testing (to be filled in)

Once tests exist, document:
- How to run the full test suite
- How to run a single test
- Whether tests must pass before committing

---

## Environment Setup (to be filled in)

Document here:
- Required runtime versions (Node, Python, Go, etc.)
- How to install dependencies
- Required environment variables and where to put them (e.g., `.env.local`)
- Any services that must be running locally (database, message broker, etc.)

---

## Build & Run (to be filled in)

```sh
# Install dependencies
# <command here>

# Run in development mode
# <command here>

# Build for production
# <command here>
```

---

## Directory Structure (to be filled in)

Once the project has source files, document the layout here. Example template:

```
/
├── src/            # Application source code
├── tests/          # Test files
├── scripts/        # Build/utility scripts
├── docs/           # Additional documentation
└── CLAUDE.md       # This file
```

---

## Working with This Codebase as an AI

- Read this file at the start of every session.
- Before making changes, understand the existing patterns in the surrounding code.
- Match the code style of whatever file you are editing.
- Do not introduce new dependencies without discussing the trade-offs with the user.
- For exploratory questions, give a 2–3 sentence recommendation with the main trade-off before implementing.
- After pushing changes, confirm the branch and commit SHA so the user can verify.
- Update this CLAUDE.md whenever new conventions, tools, or workflows are established.
