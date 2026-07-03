# REAL BUG: security/tomoyo/network.c:317 tomoyo_write_inet_network()

**Confidence**: HIGH | **Counter**: `$->head.users.counter`

## Reasoning

| L316 (success path, from `'@'` branch) | fall‑through to `out` | YES | YES | ✅ | Balanced |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L299 | `return -EINVAL` | NO (before any get) | N/A | ✅ | |
| L303 (inside `if (param->data[0] == '@')`) | `return -ENOMEM` | NO (get returned NULL) | N/A | ✅ | `tomoyo_get_group` failed, no ref taken |
| L308 (else branch, `parse_ipaddr_union` fails) | `goto out` | NO (else path, no `tomoyo_get_group` call) | YES (`tomoyo_put_group` at out) | ❌ | Excess put on NULL/uninitialized group |
| L314 (from else branch, `parse_number_union`/port check fails) | `goto out` | NO | YES | ❌ | Same as above, no get on else path |
| L314 (from `'@'` branch, `parse_number_union`/port check fails) | `goto out` | YES (get succeeded earlier) | YES | ✅ | Balanced |
| L316 (success path, from else branch) | fall‑through to `out` | NO | YES | ❌ | `tomoyo_put_group` called without get |
| L316 (success path, from `'@'` branch) | fall‑through to `out` | YES | YES | ✅ | Balanced |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The unconditional `tomoyo_put_group(e.address.group)` at `out:` is reached by paths where no get was performed (the else branch and its error/success returns), causing an excess put.
```
