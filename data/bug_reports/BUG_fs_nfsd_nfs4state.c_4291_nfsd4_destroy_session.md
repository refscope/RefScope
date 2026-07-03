# REAL BUG: fs/nfsd/nfs4state.c:4291 nfsd4_destroy_session()

**Confidence**: HIGH | **Counter**: `$->se_ref.counter`

## Reasoning

| Early return at out label (no session obtained)  | error        | NO        | N/A       | ✅        |                                                                                                                                    |

## Full Response

```
```
| Line/Path                                       | Return Type | GET Done? | PUT Done? | Balanced? | Notes                                                                                                                             |
|-------------------------------------------------|-------------|-----------|-----------|-----------|-----------------------------------------------------------------------------------------------------------------------------------|
| Early return if compound session & not last op  | error        | NO (before get) | N/A       | ✅        | get hasn’t happened; ref_held_by_me=0                                                                                            |
| find_in_sessionid_hashtbl returns NULL            | error        | NO (get failed) | N/A       | ✅        | no session, no reference                                                                                                          |
| mach_creds_match fails → goto out_put_session    | error        | YES       | YES       | ✅        | reference from find is put; mark_session_dead_locked not called; balanced                                                         |
| mark_session_dead_locked fails → goto out_put_session | error    | YES       | YES       | ✅        | reference from find is still held and correctly put; mark did not consume it                                                      |
| **mark_session_dead_locked succeeds → out_put_session** | success  | YES       | YES       | ❌        | **mark already consumed the reference(s)** — internal put(s) inside mark, then explicit nfsd4_put_session_locked causes double-put → REFCOUNT EXCESS |
| Early return at out label (no session obtained)  | error        | NO        | N/A       | ✅        |                                                                                                                                    |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
After a successful `mark_session_dead_locked(ses, 1 + ref_held_by_me)`, the session's hash reference (and any compound reference) are already consumed inside `mark_session_dead_locked`, making the subsequent `nfsd4_put_session_locked(ses)` at line 4291 an excess decrement — a double-put on the session's `se_ref`.```
```
