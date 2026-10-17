# AGENTS.md

## Commits

- Never commit or push to `main`. Always work on a separate branch.
- Never push. Only the user can push to a remote repository.

## Code Comments

- Write self-describing code with helpful method and variable names instead of comments.
- Add comments sparingly, only for confusing or obscure code blocks. Keep them brief.
- Never describe business rationale in comments.

## Code Style

- Always give arrow functions a block body `{ ... }` with an explicit return. Never use implicit-return arrow functions.

## Tests

- Each file has exactly one `describe` block.
- Never define functions, helpers, variables or constants inside a `describe` block. 