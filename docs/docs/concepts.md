---
sidebar_position: 2
---

# Concepts

## Policy

A **policy** targets a single resource type and pairs a condition tree (the *rule*) with an
**effect**:

- **allow** — the resource is compliant only when its rule matches (an allow-list).
- **deny** — the resource violates the policy when its rule matches (a deny-list).

A policy may also carry an optional **match** selector that narrows which resources it
applies to, a **severity**, and **remediation** guidance.

## Condition tree

Rules are declarative trees built from four node types: `all` (conjunction), `any`
(disjunction), `not` (negation), and leaf **comparisons** of the form
`{attribute, operator, value}`. Comparisons are evaluated by a fixed
[operator registry](policy-syntax.md#operators) — policies never execute arbitrary code.

## Resource snapshot

Scanning normalises each workspace object into a flat **snapshot** of attributes (name,
owner, owner type, tags, and type-specific fields). Rules are evaluated against these
snapshots. The attributes available per resource type are a fixed contract that policy
validation checks against.

## Finding

Evaluating one policy against one applicable resource produces a **finding** — compliant or
violating — with the policy's severity and remediation guidance.

## Approval lifecycle

Policies move through `draft → in_review → approved`, with `rejected` and `archived` as
terminal-ish states. Only **approved** policies are run by scans. Transitions are gated by
[roles](approvals.md).

## Remediation cycle

Each violation is tracked as a **remediation item** (`open → in_progress → resolved`, or
`waived`). Re-scans reconcile open items automatically: an item whose violation has cleared
is auto-resolved.
