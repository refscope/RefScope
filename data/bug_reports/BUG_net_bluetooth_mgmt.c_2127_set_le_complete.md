# REAL BUG: net/bluetooth/mgmt.c:2127 set_le_complete()

**Confidence**: HIGH | **Counter**: `$->sk->sk_refcnt.refs.counter`

## Reasoning

k == cmd->sk` → two `sock_put` on the same sk for one actual reference. | The contract states the GET is conditional; the code unconditionally puts `match.sk` if the pointer is set. When the reference was not taken, this causes a double put on `cmd->sk`, matching the refcount excess put warning. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2109 | early return (err==-ECANCELED or invalid) | NO (no `settings_rsp`, no get on `match.sk`; cmd’s sk reference held but not released here) | NO (`mgmt_pending_free` not called) | ⚠️ Leak of `cmd->sk` reference, not an excess put | Not the reported balance – excess put involves a double put. |
| L2112→L2115 (goto done) | `goto done` (status != 0) | NO (no `settings_rsp`) | YES (`mgmt_pending_free` puts `cmd->sk`) | ✅ | Only original reference released. |
| L2117→L2126 (success, status==0) | normal end (after `settings_rsp`, `new_settings`, `sock_put(match.sk)`, then `mgmt_pending_free`) | **CONDITIONAL** – `settings_rsp` may or may not call `sock_hold` on the sk stored in `match.sk` (per contract). | YES: `if (match.sk) sock_put(match.sk)` **unconditionally** plus `mgmt_pending_free` puts `cmd->sk` | ❌ **EXCESS PUT** if `settings_rsp` did **not** acquire a reference, `match.sk` is non‑NULL, and `match.sk == cmd->sk` → two `sock_put` on the same sk for one actual reference. | The contract states the GET is conditional; the code unconditionally puts `match.sk` if the pointer is set. When the reference was not taken, this causes a double put on `cmd->sk`, matching the refcount excess put warning. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

`settings_rsp` conditionally takes a reference (`sock_hold`) but the success path unconditionally does `sock_put(match.sk)` if the pointer is non‑NULL. When `match.sk == cmd->sk` and the GET was skipped, the subsequent `sock_put` plus `mgmt_pending_free`'s `sock_put` produce an extra put on `cmd->sk`, triggering the excess put warning.
```
