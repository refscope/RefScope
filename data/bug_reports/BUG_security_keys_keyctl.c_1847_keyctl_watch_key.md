# REAL BUG: security/keys/keyctl.c:1847 keyctl_watch_key()

**Confidence**: HIGH | **Counter**: `$->usage.refcount.refs.counter`

## Reasoning

| L1815 (ret = 0) | success, fall‑through | YES (ownership transferred) | YES | N/A (list owns ref) | YES | ✅ | watch added, watch = NULL, list will later kref_put |

## Full Response

```
| Line | Return Type | GET Done? (watch init) | GET Done? (wqueue) | PUT Done? (watch) | PUT Done? (wqueue) | Balanced? | Notes |
|------|-------------|------------------------|--------------------|-------------------|--------------------|-----------|-------|
| L1781 | error (-EINVAL) | NO | NO | N/A | N/A | ✅ | early param check, no get |
| L1785 | error (key_ref ERR) | NO | NO | N/A | N/A | ✅ | lookup_user_key failed |
| L1791 | goto err_key (key_put) | NO | NO (get_watch_queue returned ERR) | N/A | N/A (no get) | ✅ | get_watch_queue failed, no ref taken |
| L1797 | goto err_wqueue | NO | YES | N/A | YES (put_watch_queue at L1845) | ✅ | wlist alloc failed |
| L1801 | goto err_wlist | NO | YES | N/A | YES (put_watch_queue) | ✅ | watch alloc failed, no init_watch |
| **L1806** | goto err_watch | **YES** | YES | **NO** (kfree only) | YES | **❌ LEAK** | security_watch_key failed; kfree bypasses kref_put |
| **L1815 (ret ≠ 0)** | fall‑through to err_watch | **YES** | YES | **NO** (kfree only) | YES | **❌ LEAK** | add_watch_to_object failed; watch not NULL, kfree bypasses kref_put |
| L1815 (ret = 0) | success, fall‑through | YES (ownership transferred) | YES | N/A (list owns ref) | YES | ✅ | watch added, watch = NULL, list will later kref_put |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`init_watch` unconditionally sets usage kref to 1, but error paths (security_watch_key failure and add_watch_to_object failure) free the watch with `kfree` without calling `kref_put`, leaking the refcount.
```
