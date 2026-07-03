# REAL BUG: net/sunrpc/auth_gss/auth_gss.c:886 gss_pipe_destroy_msg()

**Confidence**: HIGH | **Counter**: `gss_msg->count.refs.counter`

## Reasoning

t saturation warning. The code appears to have an off‑by‑one: the developer likely intended the `refcount_inc` to compensate for the reference that would be dropped by `gss_unhash_msg`, but then forgot that the final `gss_release_msg` would still be reached on this path, resulting in a double‑put.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L886 (msg->errno >= 0) | normal (function‑end) | NO | YES (gss_release_msg at L886) | Likely balanced¹ | Single put for the reference held by the caller; if that was the last ref, object is freed. |
| L878–L882→L886 (msg->errno < 0) | normal | YES (refcount_inc at L878) | YES: gss_release_msg inside if (L882) + gss_release_msg at L886 | ❌ LEAK / excess put if gss_unhash_msg also releases | `refcount_inc` adds +1. If the message initially had refcount 1, the net refcount after inc is 2. `gss_unhash_msg` is likely a put (causing a drop to 1 or 0). Then the two explicit `gss_release_msg` calls would over‑drop, triggering the “excess put” warning at L886. |

¹ The single put on the “errno >= 0” path is correct as long as the caller passed a valid reference; it is not the source of the warning.

**Analysis**  
The warning “refcount excess put” at line 886 specifically flags the final `gss_release_msg(gss_msg)` that executes *after* the `if (msg->errno < 0)` block. When `errno < 0`, the function first calls `refcount_inc` (unconditional get), then `gss_unhash_msg`, then `gss_release_msg` inside the block, and finally the second `gss_release_msg` outside the block. The `gss_unhash_msg` call is undocumented here but its name strongly suggests it removes the message from a hash table and in many sunrpc patterns also drops a reference (a common “unhash and put” idiom). If `gss_unhash_msg` indeed calls `gss_release_msg` (or otherwise decrements the refcount), then the total number of puts on this path becomes three (unhash + inside‑if release + final release) while only one extra reference was taken (the `refcount_inc`). This leads to an excess decrement and triggers the refcount saturation warning. The code appears to have an off‑by‑one: the developer likely intended the `refcount_inc` to compensate for the reference that would be dropped by `gss_unhash_msg`, but then forgot that the final `gss_release_msg` would still be reached on this path, resulting in a double‑put.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH
```
