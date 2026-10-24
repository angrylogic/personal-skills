# Personal Skills

A personal skills plugin for Codex and Claude Code. Both hosts load the same
`skills/` directory.

## Install

Install a recent Codex or Claude Code client with plugin support and Git. Private
repositories require GitHub access on the installing machine. Installing this
skills-only plugin does not require Python; the upstream maintenance scripts do.

### Codex

Run in your terminal:

```sh
codex plugin marketplace add angrylogic/personal-skills
codex plugin add personal-skills@angrylogic-personal
codex plugin list --marketplace angrylogic-personal
```

Start a new session after installation. In Codex clients that manage installation
through the Plugins Directory, choose **Personal Skills** and install
**personal-skills** there. Commands and availability vary by client version.

### Claude Code

Run in your terminal to install for your user account:

```sh
claude plugin marketplace add angrylogic/personal-skills
claude plugin install personal-skills@angrylogic-personal
claude plugin list
```

Start a new session, or run `/reload-plugins` in an existing session. Skills appear
under `/personal-skills:<skill-name>`, for example `/personal-skills:grill-me`.
For a project installation, add `--scope project` to the install command.

## Upgrade

### Codex

Refresh the marketplace, then reinstall the plugin from the refreshed source:

```sh
codex plugin marketplace upgrade angrylogic-personal
codex plugin remove personal-skills@angrylogic-personal
codex plugin add personal-skills@angrylogic-personal
codex plugin list --marketplace angrylogic-personal
```

Start a new session. In clients using the Plugins Directory, refresh the source
and update or reinstall **personal-skills** there instead.

### Claude Code

Refresh the marketplace listing and update the installed plugin:

```sh
claude plugin marketplace update angrylogic-personal
claude plugin update personal-skills@angrylogic-personal
claude plugin list
```

Start a new session or run `/reload-plugins`. If installed with `--scope project`,
pass that same scope to `claude plugin update`. You can enable automatic updates
in `/plugin` → **Marketplaces** → **angrylogic-personal** → **Enable auto-update**.

These commands update your installed copy of this personal plugin. To merge a
skill author's newer upstream changes into this repository, use the separate
[upstream maintenance workflow](#import-and-maintain-upstream-skills) below.

## Develop from a local checkout

```sh
git clone https://github.com/angrylogic/personal-skills.git
cd personal-skills
```

Register this directory instead of GitHub when developing:

```sh
# Codex
codex plugin marketplace add .
codex plugin add personal-skills@angrylogic-personal

# Claude Code
claude plugin marketplace add .
claude plugin install personal-skills@angrylogic-personal
```

Choose either the GitHub source or local checkout for this marketplace. If already
registered from the other source, remove its registration with
`codex plugin marketplace remove angrylogic-personal` or
`claude plugin marketplace remove angrylogic-personal` before adding the new one.

For local-source upgrades, run `git pull --ff-only` in the checkout, then follow
the plugin reinstall/update steps above. Codex's marketplace upgrade command
refreshes Git sources; a local directory already reflects its checkout contents.

Claude can also load the checkout directly for one development session:

```sh
claude --plugin-dir .
```

Restart that session after edits. This avoids installing a cached copy.

## Add a skill

Create `skills/<skill-name>/SKILL.md`, using lowercase names with hyphens:

```markdown
---
name: my-skill
description: Describe what this skill does and when to use it.
---

Write the instructions for this workflow here.
```

Keep instructions portable between hosts. Add scripts, references, and assets
inside the skill's directory when needed, and refer to them using paths relative
to the skill. Optional Codex UI metadata belongs in `agents/openai.yaml` within
that skill. Keep host-specific features out of shared instructions unless the
skill explains the alternative for the other host.

In Claude Code, invoke a skill as `/personal-skills:my-skill`. In Codex, select it
from the skills menu or invoke `$my-skill`.

## Maintain and validate

- Keep the name, version, and description consistent across `plugin.json`,
  `.codex-plugin/plugin.json`, and `.claude-plugin/plugin.json`.
- Bump all three versions when releasing changes so cached installs can update.
- Validate Claude packaging with `claude plugin validate .` when Claude is installed.
- Installed plugins may use cached copies. Refresh the marketplace and update the
  installed plugin after changes; restart the session. Use Claude's `--plugin-dir`
  during development to load the checkout directly.

The root `plugin.json` is the portable Agent Plugins manifest. The two hidden
plugin manifests support the Codex compatibility format and Claude Code.
Each host has its own marketplace catalog pointing to this repository root.

Format references: [OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins),
[Claude plugin manifest](https://code.claude.com/docs/en/plugins-reference), and
[Claude marketplaces](https://code.claude.com/docs/en/plugin-marketplaces).

## Import and maintain upstream skills

Use Python 3.10+ and Git. These commands store provenance in the imported
`SKILL.md` frontmatter, with no separate lockfile or baseline files:

```yaml
metadata:
  upstream_repository: "https://github.com/OWNER/PACK.git"
  upstream_revision: "<full resolved commit SHA>"
  upstream_path: "skills/example"
```

Other metadata and frontmatter comments are preserved. The three
`upstream_*` keys are reserved for this tooling; leave their values JSON-quoted
as written by the script. Existing `metadata` must use a block mapping (rather
than inline `{...}` syntax). Skills containing symlinks or submodules are rejected.

Import a directory from a skill pack, optionally choosing a local folder name:

```sh
python3 scripts/skills.py import example https://github.com/OWNER/PACK.git skills/example --ref main
```

`--ref` accepts a branch, tag, or commit and defaults to the upstream repository's
`HEAD`. The resolved full commit SHA is recorded. Import refuses to overwrite an
existing skill. A different local folder name does not rewrite the skill's own
frontmatter `name` or its internal references. Review imported instructions,
scripts, dependencies, and license terms before using or redistributing them;
repository-level licenses may need to be copied separately.

Show your changes against the recorded upstream baseline:

```sh
python3 scripts/skills.py diff example
python3 scripts/skills.py diff example > /tmp/example.patch
# Optionally compare directly against a newer upstream revision:
python3 scripts/skills.py diff example --ref main
```

The diff includes additions, deletions, binary changes, and executable modes,
and excludes the three provenance fields. It uses `base/` and `local/` path
prefixes; apply from a skill directory with `git apply -p2 /tmp/example.patch`.
Exit codes are 0 for no changes, 1 for differences, and 2 for errors.

Merge a new upstream revision with your local changes:

```sh
# Preview in a new directory first:
python3 scripts/skills.py update example --ref main --output /tmp/example-review
# Or apply a clean merge directly:
python3 scripts/skills.py update example --ref main
```

The update performs a three-way merge using the recorded revision as the base.
A clean update preserves local edits and advances `upstream_revision`. Commit
local changes first so Git provides an additional recovery point. The scripts
never create commits, push, install skills, or execute imported code.

On conflicts, the command exits 2 and leaves the skill and its recorded revision
unchanged. With `--output`, it writes a review tree containing conflict markers
for text conflicts; binary and add/delete conflicts keep the local file when
present, otherwise the upstream file. Check every reported conflict, including
whether a file should be deleted. Resolve the review tree manually, then copy it
back into `skills/example/` (including removing deleted files) and set
`metadata.upstream_revision` to the full SHA of the revision you merged. Review
trees produced by conflicted updates deliberately omit provenance so they cannot
silently claim to be fully merged. Use a pinned commit with `--ref` while resolving
conflicts so the target cannot move. You can inspect that commit with
`git ls-remote <repository> <branch-or-tag>` before starting.

Every diff or update retrieves upstream files using Git, so upstream access and
availability of the recorded commit are required. There is no persistent cache.
Use a local clone or mirror as the repository source if offline access is needed.

Run the isolated local integration tests with:

```sh
python3 -m unittest discover -s tests -v
```

## Included skills

- `writing-for-agents`: Matt Pocock’s guidance for writing skills and other agent
  documents, imported from [`mattpocock/skills`](https://github.com/mattpocock/skills)
  at `5beb35b040e3de97e54fa9e386d7e42d15c295c2`. Its supporting
  `SKILL-MECHANICS.md` and Codex UI metadata are included. It has no dependencies
  on other skills in that repository. The upstream MIT notice is preserved in
  [licenses/mattpocock-skills-LICENSE](licenses/mattpocock-skills-LICENSE).

For every upstream import, inspect the skill and its supporting files for
references to other skills, follow required dependencies recursively at the same
commit, and verify references after copying. See [AGENTS.md](AGENTS.md).

The same pinned Matt Pocock revision also supplies:

- `grilling`: the shared interview workflow.
- `grill-me`: an explicit invocation of `grilling`.
- `grill-with-docs`: combines `grilling` with `domain-modeling`.
- `domain-modeling`: the required glossary and ADR workflow, including its format
  templates. It has no further skill dependencies.

The two grilling wrappers use relative links to the imported skills in place of
upstream’s Claude-specific Skill tool calls. These portability changes are visible
through `scripts/skills.py diff`. All four retain their upstream frontmatter and
Codex invocation policies, plus the recorded provenance. The same upstream MIT
license notice above covers these imports.

Also imported at that revision, without changes beyond provenance:

- `to-spec`: synthesize a conversation into a spec for the configured tracker.
- `to-tickets`: break a plan or spec into tickets with blocking dependencies.
- `setup-matt-pocock-skills`: their shared configuration prerequisite, including
  GitHub, GitLab, and local Markdown tracker templates, domain documentation
  guidance, and the triage label template. Its `triage` and `wayfinder` references
  describe optional integrations; those skills are not required or imported.

Run `setup-matt-pocock-skills` in a consuming project before using `to-spec` or
`to-tickets` if that project's tracker conventions are not already configured.

- `codebase-design`: deep-module vocabulary, interface and seam design guidance,
  with `DEEPENING.md` and `DESIGN-IT-TWICE.md`. Imported from the same pinned Matt
  Pocock revision with no changes beyond provenance. It has no dependencies on
  other skills; its relative reference links resolve within the skill directory.

- `improve-codebase-architecture`: scans for deepening opportunities, produces a
  visual HTML report, and explores the selected improvement through grilling.
  Includes `HTML-REPORT.md`; its `codebase-design`, `grilling`, and
  `domain-modeling` dependencies are already included at the same pinned revision.
  Claude-specific Skill tool calls are replaced with relative skill references;
  all other upstream content and explicit invocation settings are preserved.
