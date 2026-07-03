# REAL BUG: fs/ocfs2/dlm/dlmthread.c:337 dlm_run_purge_list()

**Confidence**: MEDIUM | **Counter**: `$->refs.refcount.refs.counter`

## Reasoning

_purge_lockres at L316 | ❌ EXCESS PUT | smatch tracks excess put at L337; dlm_purge_lockres is a PUT (per contract) – it likely already dropped the reference, making L337 a double‑put. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L300 (break) | break → end of function | NO (before get) | NO | ✅ | |
| ~L311 (continue) | continue → next iteration | NO (before get) | NO | ✅ | |
| L315 (dlm_lockres_get) → L337 (explicit put) | loop iteration end (path that purges) | YES (unconditional get at L315) | YES (explicit put at L337) but also potentially via dlm_purge_lockres at L316 | ❌ EXCESS PUT | smatch tracks excess put at L337; dlm_purge_lockres is a PUT (per contract) – it likely already dropped the reference, making L337 a double‑put. |
| Loop exit after iteration | end of function | N/A (already accounted per iteration) | N/A | See row above | |

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  

The unconditional `dlm_lockres_get` at L315 acquires a reference. The contract for `dlm_purge_lockres` (L316) states it is a PUT (releases a reference). The explicit `dlm_lockres_put` at L337 is therefore a second release for the same reference, triggering the “refcount excess put” warning. Without the source of `dlm_purge_lockres` we assume it drops a reference; the static analysis confirms the excess.
```
