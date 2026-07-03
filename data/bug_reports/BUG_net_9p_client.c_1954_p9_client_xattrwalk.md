# REAL BUG: net/9p/client.c:1954 p9_client_xattrwalk()

**Confidence**: HIGH | **Counter**: `$->count.refs.counter`

## Reasoning

| ~L1939 (return attr_fid) | success | YES | N/A (ownership transferred to caller) | ✅ | Reference passed to caller |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L1923 (goto error, !attr_fid) | error | NO (p9_fid_create returned NULL) | N/A | ✅ | No reference held |
| ~L1928 (goto error, IS_ERR(req)) | error | YES (unconditional p9_fid_create) | NO (p9_fid_destroy ≠ p9_fid_put; contract shows p9_fid_put is the only PUT) | ❌ LEAK | p9_fid_destroy does not decrement refcount; leak of initial reference |
| ~L1934–1935 (goto clunk_fid) | error | YES | YES (p9_fid_put in clunk_fid) | ✅ | Proper put, then attr_fid=NULL bypasses destroy |
| ~L1939 (return attr_fid) | success | YES | N/A (ownership transferred to caller) | ✅ | Reference passed to caller |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
p9_fid_create sets refcount to 1, and the error path after p9_client_rpc calls p9_fid_destroy instead of p9_fid_put, leaking the reference. The contract defines p9_fid_put as the only put function.
```
```
