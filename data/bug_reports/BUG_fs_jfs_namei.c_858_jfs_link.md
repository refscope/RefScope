# REAL BUG: fs/jfs/namei.c:858 jfs_link()

**Confidence**: HIGH | **Counter**: `$->i_count.counter`

## Reasoning

| L858 (return rc, success path) | success (rc==0) | YES (ihold at L833) | NO | ❌ LEAK | d_instantiate takes its own ref, leaving ihold reference leaked |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L803 (return -EROFS) | error | NO (before ihold) | N/A | ✅ | early readonly check |
| L816 (goto out_tx) | error (get_UCSname fail) | NO (before ihold) | N/A | ✅ | |
| L819 (goto free_dname) | error (dtSearch fail) | NO (before ihold) | N/A | ✅ | |
| L825 (goto free_dname) | error (dtInsert fail) | NO (before ihold) | N/A | ✅ | |
| L841 (iput, then fall‑through to L858) | error (txCommit fail) | YES (ihold at L833) | YES (iput at L841) | ✅ | error path releases ihold |
| L858 (return rc, success path) | success (rc==0) | YES (ihold at L833) | NO | ❌ LEAK | d_instantiate takes its own ref, leaving ihold reference leaked |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
ihold(ip) at L833 is never put on the success path; d_instantiate does not consume the reference, creating a permanent leak.
```
