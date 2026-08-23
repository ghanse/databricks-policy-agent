# Databricks Policy Agent docs

Documentation site for [databricks-policy-agent](https://github.com/ghanse/databricks-policy-agent),
built with [fumadocs](https://fumadocs.dev) and deployed to GitHub Pages.

## Local development

From the repo root:

```bash
make docs-install   # one-time: install bun deps
make docs-serve     # regenerate the API reference, build, and run next dev — http://localhost:3000
```

## Build

```bash
make docs-build     # regenerate the API reference and static-export to docs/site
```

The `docs-publish.yml` workflow runs the same build and publishes `docs/site` to GitHub Pages
on every push to `main` that touches `docs/**`.

## Authoring

Hand-written pages live in `content/docs/` as `.mdx` files, ordered by
`content/docs/meta.json`. Frontmatter fields:

```yaml
---
title: Page title
description: Short summary used as the page subtitle and meta description.
---
```

Components available out of the box: `Tabs` / `Tab`, `Callout`, `Steps` / `Step` — imported
from `fumadocs-ui/components/...` at the top of each MDX file.

## API reference

The pages under `content/docs/api/` are generated from the library's Google-style docstrings
by [pydoc-markdown](https://niklasrosenstein.github.io/pydoc-markdown/) (see
`pydoc-markdown.yml`) and must not be edited by hand. `make docs-build` regenerates them
before every build.
