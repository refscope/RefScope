# REAL BUG: fs/ocfs2/dlm/dlmdomain.c:2208 dlm_register_domain()

**Confidence**: MEDIUM | **Counter**: `$->dlm_refs.refcount.refs.counter`

## Reasoning

n failure) | error (ret) | YES (alloc L2162) | **YES (dlm_put L2189)** | ❌ **EXCESS PUT** | dlm_put on error path; smatch reports the refcount goes negative, indicating **dlm_join_domain already released the reference** (ownership transfer) — our extra put creates a double-put / use-after-free |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2113 (goto leave, strlen too long) | error (-ENAMETOOLONG) | NO | NO | ✅ | No ref acquired |
| L2119 (goto leave, signal pending) | error (-ERESTARTSYS) | NO | NO | ✅ | No ref acquired |
| L2145 (goto leave, protocol mismatch) | error (-EPROTO) | NO | NO | ✅ | Looked-up dlm, no get |
| L2150 (goto leave, existing domain joined) | success (ret=0) | YES (__dlm_get L2149) | NO | ✅ | Caller will later put |
| L2167 (goto leave, alloc failure) | error (-ENOMEM) | NO | NO | ✅ | |
| L2187 (goto leave, join success) | success (ret=0) | YES (alloc L2162) | NO | ✅ | Caller will put |
| L2190 (goto leave, join failure) | error (ret) | YES (alloc L2162) | **YES (dlm_put L2189)** | ❌ **EXCESS PUT** | dlm_put on error path; smatch reports the refcount goes negative, indicating **dlm_join_domain already released the reference** (ownership transfer) — our extra put creates a double-put / use-after-free |

**VERDICT: REAL_BUG**  
**CONFIDENCE: MEDIUM**  
The error path after `dlm_join_domain` failure calls `dlm_put(dlm)`, but the callee (as deduced from smatch’s intra‑procedural refcount tracking) already releases the reference on failure. This double-put triggers the “refcount excess put” warning at the function return (line 2208). Without `dlm_join_domain` source we assume the tool’s analysis is correct; a follow‑up review of that callee is recommended.
```
