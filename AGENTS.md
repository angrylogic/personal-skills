# Upstream skill imports

Use `scripts/skills.py` to import skills and record their upstream repository,
full commit SHA, and source directory in `SKILL.md` frontmatter.

Before importing a skill, inspect every file in its directory for references to
other skills or resources in the upstream repository. Follow those references
recursively and import required skills from the same pinned commit. Distinguish
required dependencies from examples and optional suggestions. Preserve referenced
supporting files and check that their paths resolve in this repository; adjust
paths when flattening the upstream layout requires it. Report unresolved or
ambiguous dependencies rather than silently omitting them.

Preserve upstream license notices. Keep imports otherwise unchanged so local
customizations remain visible through `scripts/skills.py diff`. Summarize the
imported set and any dependency or compatibility changes.
