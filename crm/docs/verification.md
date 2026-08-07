# Verification contract

Set `harness.json:test_command` to the project's fast, deterministic test or
verification command. The command is run by `./init.sh` after the harness
metadata checks.

Every feature should define acceptance criteria that can be demonstrated by:

1. automated tests, checks, or builds; or
2. a documented manual procedure when automation is not practical.

Verification reports must include the exact command or procedure, its result,
and the relevant files or artifacts. “It works” is not evidence.
