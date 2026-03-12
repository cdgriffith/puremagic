---
name: changelog
description: Update the CHANGELOG.md changelog file with new entries
user_invocable: true
---

# Changelog Skill

When updating the `CHANGELOG.md` file, follow these rules:

## Entry Format

Each entry is a single bullet point starting with `- `:

```
- {Verb} {description}
```

## Verbs and Ordering

Entries MUST use one of these four starting verbs, and MUST appear in this order within each version section:

1. **Adding** — new features
2. **Changing** — modifications to existing behavior
3. **Fixing** — bug fixes
4. **Removing** — removed features or deprecated items

## GitHub Issue Entries

- Entries that reference a GitHub issue include the issue number after the verb: `* Fixing #725 description...`
- Within each verb group, entries WITH issue numbers come FIRST, sorted by issue number ascending (smallest to largest)
- Entries WITHOUT issue numbers follow after

## Thanks Attribution

- When an entry references a GitHub issue, thank the issue author by their **GitHub display name** (not username)
- Look up the display name via `gh api users/{username} --jq '.name // .login'`
- Format: `(thanks to {display name})`
- If multiple people contributed (e.g., reporter and commenter with the fix), thank all of them
- The thanks attribution goes at the end of the entry

## Example

```
Version 1.27
------------

- Adding #92 include py.typed in sdist (thanks to Nicholas Bollweg - bollwyvl)
- Adding #93 Improve PDF file detection, fix json description (thanks to Péter - peterekepeter)
- Adding new verbose output to command line with `-v` or `--verbose`
- Fixing #96 #86 stream does not work properly on opened small files (thanks to Felipe Lema and Andy - NebularNerd)
- Removing expected invalid WinZip signature
```
