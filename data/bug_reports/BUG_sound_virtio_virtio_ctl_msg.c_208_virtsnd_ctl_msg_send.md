# REAL BUG: sound/virtio/virtio_ctl_msg.c:208 virtsnd_ctl_msg_send()

**Confidence**: HIGH | **Counter**: `$->ref_count.refs.counter`

## Reasoning

Fixing this would remove the extra unref in the error block (or skip the on_exit unref only on that path). As it stands, the double‑put is a **real bug**.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L139‑L176 (success, nowait, timeout/interrupt) | return rc at end via on_exit label | YES (unconditional ref at L139) | YES (single unref at on_exit label) | ✅ | Normal paths: one get‑one put. |
| L166‑L173 (virtqueue_add_sgs failure) → L208 on_exit | return rc via on_exit | YES | **TWO unrefs**: one at L170 inside `if(rc)` block, then a second at the on_exit label (L208) | ❌ | Double put: excess reference. The explicit unref on error is immediately followed by the unconditional unref at on_exit. |

**Explanation:**
- `virtsnd_ctl_msg_ref()` (unconditional get) is called at L139, so every exit must call exactly one `virtsnd_ctl_msg_unref()`.
- The error path for `virtqueue_add_sgs()` failure (L166‑L173) calls `virtsnd_ctl_msg_unref(msg)` at L170 and then `goto on_exit`.
- `on_exit:` at L208 also calls `virtsnd_ctl_msg_unref(msg)`.  
  → Two puts for one get, leading to refcount underflow and the “excess put” at L208.

Fixing this would remove the extra unref in the error block (or skip the on_exit unref only on that path). As it stands, the double‑put is a **real bug**.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
```
