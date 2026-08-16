# Coding Skill

> Architect, implement, refactor, and test production-grade software with strong typing, modular design, current documentation, and empirical verification.

## When to Use

Use this skill for:

* New features, modules, classes, functions, and scripts
* Bug fixes and refactoring
* APIs, SDKs, integrations, and automation
* Unit, integration, and E2E tests
* CLI tools and data pipelines

## Workflow

### 1. Inspect First

Before coding:

* Inspect the project structure.
* Read relevant existing files.
* Search for related symbols, usages, types, utilities, and tests.
* Identify language, framework, dependencies, test runner, linter, and type checker.
* Follow existing project conventions.

**Never modify code blindly.**

### 2. Research When Needed

If you lack current context, especially for external libraries, APIs, SDKs, frameworks, or rapidly changing technologies:

* Use `web_search` to find current information.
* Use `read_url` to inspect official documentation, API references, GitHub READMEs, migration guides, or specifications.
* Prefer official/current sources.
* Verify the version being used before relying on an API.

**Do not guess external APIs or outdated behavior when documentation can verify it.**

### 3. Design

Define clear:

* Interfaces and function signatures
* Types/schemas
* Inputs and outputs
* Error behavior
* Dependencies

Follow:

* Single Responsibility
* DRY
* Loose coupling
* High cohesion
* Defensive programming

### 4. Implement

* Use `write_file` for new files.
* Use `edit_file` for targeted changes.
* Keep changes minimal and focused.
* Preserve existing public APIs where possible.
* Add explicit types and useful documentation.
* Handle errors explicitly.
* Never expose secrets.

### 5. Test & Verify

Add tests for:

* Happy paths
* Edge cases
* Invalid inputs
* Expected failures
* Regressions

Run the project's actual:

* Tests
* Build
* Type checker
* Linter
* Formatter

If something fails, investigate the error, fix it, and run verification again.

**Never claim something passes unless you actually ran it.**

### 6. Final Review

Check that:

* [ ] Requirements are fully implemented
* [ ] Existing behavior is preserved where required
* [ ] Tests pass
* [ ] Types/lint/build pass where applicable
* [ ] No debug/dead code remains
* [ ] Documentation is updated if needed
* [ ] External APIs were verified when necessary

## Tool Guidelines

| Task                       | Tool                           |
| -------------------------- | ------------------------------ |
| Explore project            | `list_directory`               |
| Read code                  | `read_file`                    |
| Find symbols               | `search_files` / `grep_search` |
| Create files               | `write_file`                   |
| Modify files               | `edit_file`                    |
| Run tests/builds           | `run_command`                  |
| Current technical research | `web_search`                   |
| Read documentation/URLs    | `read_url`                     |

## Expected Response

````markdown
# Implementation Summary: [Feature]

## Overview
What changed and why.

## Key Changes
- `path/to/file`: What changed.
- `path/to/test`: What was tested.

## Verification
```text
[Actual test/build/lint/type-check output]
````

## Status

* Tests: PASS / FAIL / NOT RUN
* Type checking: PASS / FAIL / N/A
* Linting: PASS / FAIL / N/A
* Build: PASS / FAIL / N/A

## Usage

Brief example of how to use the implementation.

```

## Core Principle

> **Inspect first. Research when necessary. Implement cleanly. Test empirically. Never guess when the codebase or official documentation can provide the answer.**
```
