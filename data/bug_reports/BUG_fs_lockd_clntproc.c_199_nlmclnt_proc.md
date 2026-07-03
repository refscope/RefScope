# REAL BUG: fs/lockd/clntproc.c:199 nlmclnt_proc()

**Confidence**: HIGH | **Counter**: `$->a_count.refs.counter`

## Reasoning

| L194 (via else) | cmd unrecognised (neither SETLK/SETLKW nor GETLK) | YES (alloc) | NO | ❌ **LEAK** | call allocated but never used or released; returns -EINVAL with ref held |

## Full Response

```
| Line | Condition | GET Done? | PUT Done? | Balanced? | Notes |
|------|-----------|-----------|-----------|-----------|-------|
| L167 | call == NULL | NO (before alloc) | N/A | ✅ | early no-alloc return |
| L174 | !fl->fl_u.nfs_fl.owner | YES (from nlm_alloc_call L166) | YES (nlmclnt_release_call L173) | ✅ | explicit release on lockowner failure |
| L194 (via nlmclnt_lock) | cmd is SETLK/SETLKW, flc_type != F_UNLCK | YES (alloc) | YES (inside nlmclnt_lock – contract says unconditional put) | ✅ | nlmclnt_lock consumes the reference |
| L194 (via nlmclnt_unlock) | cmd is SETLK/SETLKW, flc_type == F_UNLCK | YES (alloc) | UNCERTAIN (nlmclnt_unlock has conditional‑on‑path put / get; may not release the initial ref) | ⚠️ | could be leak but not needed for verdict |
| L194 (via nlmclnt_test) | cmd is GETLK | YES (alloc) | YES (inside nlmclnt_test – unconditional put) | ✅ | reference consumed |
| L194 (via else) | cmd unrecognised (neither SETLK/SETLKW nor GETLK) | YES (alloc) | NO | ❌ **LEAK** | call allocated but never used or released; returns -EINVAL with ref held |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`nlm_alloc_call` always creates a reference; the `else` branch (cmd not recognised) assigns `status = -EINVAL` and returns without a matching `nlmclnt_release_call`, leaking the call object.
```
