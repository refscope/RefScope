# REAL BUG: fs/resctrl/rdtgroup.c:4229 rdtgroup_rename()

**Confidence**: HIGH | **Counter**: `$->active.counter`

## Reasoning

| L4229 | final return | — | PUT line reported | ❌ excess | second rdtgroup_kn_put at line 4229 is the excess put |

## Full Response

```
| Line | Return Type | GET Done? (rdtgrp / new_prdtgrp) | PUT Done? | Balanced? | Notes |
|------|-------------|----------------------------------|-----------|-----------|-------|
| L4146 | early return | NO / NO (pre-get) | NO | ✅ | both pointers NULL, safe early exit |
| L4160 | goto out | COND (may be NO) | YES (both puts at L4227/L4229) | ❌ if GET failed | rdtgroup_kn_get() may fail, put always executed |
| L4167 | goto out | COND (may be NO) | YES | ❌ if GET failed | same |
| L4181 | goto out | COND (may be NO) | YES | ❌ if GET failed | same |
| L4190 | goto out | COND (may be NO) | YES | ❌ if GET failed | same |
| L4198 | goto out | COND (may be NO) | YES | ❌ if GET failed | same |
| L4211 | goto out | COND (may be NO) | YES | ❌ if GET failed | ENOMEM path |
| L4217 | success fallthrough | COND (may be NO) | YES | ❌ if GET failed | kernfs_rename zero, fallthrough |
| L4229 | final return | — | PUT line reported | ❌ excess | second rdtgroup_kn_put at line 4229 is the excess put |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`rdtgroup_kn_get()` likely wraps `kernfs_get_active()` and can fail (return NULL) without incrementing the active counter, but the function unconditionally calls `rdtgroup_kn_put()` for both groups on every path after the get calls, leading to an excess put when the get failed.
```
