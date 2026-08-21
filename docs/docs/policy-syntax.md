---
sidebar_position: 3
---

# Policy syntax (YAML)

Policies are authored in an Open Policy Agent-style YAML format. A file may contain a single
policy, a list of policies, or several documents separated by `---`.

```yaml
policy: clusters-owned-by-service-principals
description: All-purpose clusters created through the UI must be owned by a service principal.
resource_type: cluster        # job | cluster | sql_warehouse | app | serving_endpoint
effect: deny                  # allow | deny
severity: high                # low | medium | high | critical
match:                        # optional selector; omit to apply to all resources of the type
  all:
    - { attribute: cluster_source, operator: equals, value: UI }
rule:
  any:
    - { attribute: owner_type, operator: not_equals, value: service_principal }
remediation: Recreate the cluster under an approved service principal.
```

## Condition nodes

| Form | Meaning |
| --- | --- |
| `all: [ ... ]` | every child condition must hold |
| `any: [ ... ]` | at least one child condition must hold |
| `not: { ... }` | the child condition must not hold |
| `{ attribute, operator, value }` | a leaf comparison |

Attributes may use dotted paths to index nested mappings, e.g. `tags.environment`.

## Operators

`equals`, `not_equals`, `matches_regex`, `in`, `not_in`, `exists`, `absent`, `less_than`,
`greater_than`, `contains`, `has_tag`, `missing_tag`, `not_empty`,
`owner_is_service_principal`, `ttl_within`.

`exists`, `absent`, `not_empty`, and `owner_is_service_principal` ignore `value`. `not_empty`
holds when the attribute is a non-empty collection or mapping (e.g. a `tags` map with at
least one entry). `has_tag` / `missing_tag` operate on a mapping attribute (usually `tags`)
and take a tag key as `value`. `ttl_within` compares a numeric attribute against a maximum.

Validating a policy checks that every operator is registered and every attribute is valid
for the resource type, so mistakes are caught at author time rather than during a scan.
