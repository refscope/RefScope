# REAL BUG: fs/nfs/direct.c:1078 nfs_file_direct_write()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

ut_release      | YES                | YES (L1039) + YES (out_release)    | ❌ EXCESS PUT  | explicit release on error then label release |

## Full Response

```
| Line (approx) | Return Type           | GET Done?          | PUT Done?                          | Balanced?      | Notes |
|----------------|-----------------------|--------------------|------------------------------------|----------------|-------|
| L1005          | error return          | NO (before get)    | N/A                                | ✅             | result ≤ 0, dreq not allocated |
| L1017          | goto out              | NO (alloc failed)  | N/A                                | ✅             | nfs_direct_req_alloc returns NULL |
| L1026          | goto out_release      | YES (alloc OK)     | YES (L1025) + YES (out_release)    | ❌ EXCESS PUT  | explicit release then label release → double put |
| L1040          | goto out_release      | YES                | YES (L1039) + YES (out_release)    | ❌ EXCESS PUT  | explicit release on error then label release |
| L1067 (fallthrough) | out_release       | YES                | once (normal)                      | ✅             | assumes schedule_iovec does not release |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
IS_ERR(l_ctx) and nfs_start_io_direct error paths call nfs_direct_req_release(dreq) then goto out_release, which releases again, causing double kref_put.
```
