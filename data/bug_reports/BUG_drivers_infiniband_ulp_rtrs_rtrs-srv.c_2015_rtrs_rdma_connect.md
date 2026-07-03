# REAL BUG: drivers/infiniband/ulp/rtrs/rtrs-srv.c:2015 rtrs_rdma_connect()

**Confidence**: HIGH | **Counter**: `$->refcount.refs.counter`

## Reasoning

|     L1955: success (return 0) | mutex_unlock; return 0 | YES | NO | ❌ LEAK | caller’s ref still held, not dropped |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1893 (len check) | goto reject_w_err | NO (before GET) | N/A | ✅ | GET not called |
| L1897 (magic) | goto reject_w_err | NO | N/A | ✅ | |
| L1902 (version) | goto reject_w_err | NO | N/A | ✅ | |
| L1907 (con_num > 4096) | goto reject_w_err | NO | N/A | ✅ | |
| L1912 (cid >= con_num) | goto reject_w_err | NO | N/A | ✅ | |
| L1914: get_or_create_srv returns ERR | goto reject_w_err | NO (GET failed) | N/A | ✅ | IS_ERR guard, no ref |
| L1920: __find_path found srv_path, after L1924 put_srv(srv): | | | | | |
|   L1927: state != CONNECTING | mutex_unlock; goto reject_w_err | NO (already PUT) | YES (L1924) | ✅ | |
|   L1932: con_num mismatch | mutex_unlock; goto reject_w_err | NO | YES | ✅ | |
|   L1937: con[cid] exists | rtrs_srv_check_close_path; mutex_unlock; goto reject_w_err | NO | YES | ✅ | |
|   L1945: create_con fails → close_and_return_err | goto close_and_return_err | NO | YES | ✅ | srv ref already put |
|   L1950: rtrs_rdma_do_accept fails → close_and_return_err | goto close_and_return_err | NO | YES | ✅ | |
|   L1955: success (return 0) | mutex_unlock; return 0 | NO | YES | ✅ | |
| L1938: else branch (__find_path NULL): | | | | | |
|   L1940: __alloc_path fails → mutex_unlock; put_srv; goto reject_w_err | goto reject_w_err | NO (GET failed) | YES (put_srv) | ✅ | |
|   L1942: __alloc_path succeeds, then: | | | | | |
|     L1945: create_con fails → close_and_return_err | goto close_and_return_err | YES | NO | ❌ LEAK | srv ref never put, close_path doesn’t release caller’s ref |
|     L1950: do_accept fails → close_and_return_err | goto close_and_return_err | YES | NO | ❌ LEAK | same |
|     L1955: success (return 0) | mutex_unlock; return 0 | YES | NO | ❌ LEAK | caller’s ref still held, not dropped |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
In the else branch (new path creation), after __alloc_path succeeds, `get_or_create_srv()` reference is never released via `put_srv(srv)`. The existing-path case immediately drops the extra ref, but the new-path case forgets it, leaking the reference on all three paths (create_con error, do_accept error, success return). `close_path()` in the error label only releases the path’s own reference, not the caller’s.
```
