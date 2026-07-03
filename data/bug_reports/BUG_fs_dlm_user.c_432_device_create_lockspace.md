# REAL BUG: fs/dlm/user.c:432 device_create_lockspace()

**Confidence**: HIGH | **Counter**: `$->ls_count.counter`

## Reasoning

| L425 (success) | minor number        | YES (creation + find refs)    | YES (find ref put; creation ref transferred to device) | ✅ | device holds creation ref, no leak |

## Full Response

```
| Line   | Return Type                   | GET Done?                     | PUT Done?                        | Balanced? | Notes                                                                |
|--------|-------------------------------|-------------------------------|----------------------------------|-----------|----------------------------------------------------------------------|
| L411   | -EPERM                        | NO (before any get)           | N/A                              | ✅        | early permission check                                               |
| L414   | error (new_user_lockspace)    | NO (creation failed)          | N/A                              | ✅        | no lockspace created                                                 |
| L416   | -ENOENT (find fails)          | YES (creation ref from L413)  | NO (no dlm_release_lockspace)    | ❌ LEAK     | create succeeded, find failed → leak of initial lockspace reference  |
| L421‑L425 (error after register fail) | error code | YES (creation + find refs)    | YES (dlm_put_lockspace + dlm_release_lockspace) | ✅ | both references released on error path |
| L425 (success) | minor number        | YES (creation + find refs)    | YES (find ref put; creation ref transferred to device) | ✅ | device holds creation ref, no leak |

**VERDICT: REAL_BUG**
**CONFIDENCE: HIGH**
`dlm_find_lockspace_local` failure after successful `dlm_new_user_lockspace` returns -ENOENT without calling `dlm_release_lockspace`, leaking the lockspace refcount.
```
