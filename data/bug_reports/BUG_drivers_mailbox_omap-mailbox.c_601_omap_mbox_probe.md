# REAL BUG: drivers/mailbox/omap-mailbox.c:601 omap_mbox_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

Every error path after the first call to `of_get_next_available_child()` leaks the reference, and the final success return also leaks the last child reference. This is a **REAL_BUG** — refcount leak.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L458 | error (no dt) | NO (child not yet used) | N/A | ✅ | child is NULL |
| L461 | error (num_users) | NO | N/A | ✅ | |
| L468 | error (info_count=0) | NO | N/A | ✅ | |
| L472 | error (no mem) | NO | N/A | ✅ | |
| L478 | error (no match data) | NO | N/A | ✅ | |
| L483 | error (ioremap) | NO | N/A | ✅ | |
| L488 | error (no mem) | NO | N/A | ✅ | |
| L493 | error (mbox alloc fail) | depends: previous child ref held? | YES (if not first iteration) | NO | ❌ | On subsequent loop, child holds ref from previous of_get_next_available_child() |
| L495 | child = of_get_next_available_child(node, child) | YES (unconditional inc on return) | N/A | GET happens | After this, child holds ref to current child |
| L497-L500 | error (of_property tx fail) | YES | NO | ❌ LEAK | child ref not released |
| L503-L506 | error (of_property rx fail) | YES | NO | ❌ LEAK | |
| L512 | error (EINVAL) | YES | NO | ❌ LEAK | |
| L536 | error (irq < 0) | YES | NO | ❌ LEAK | return mbox->irq (negative) |
| Loop iteration i++ | (continue, child will be passed to next of_get_next_available_child) | YES on next call, previous put handled internally | ✅ (implicit) | Next call releases prev child. |
| After loop: L570 | error (controller alloc) | YES (last child) | NO | ❌ LEAK | |
| L583 | error (register fail) | YES | NO | ❌ LEAK | |
| L594 | error (runtime resume fail) | YES | NO | ❌ LEAK | |
| L600 | error (runtime put fail) | YES | NO | ❌ LEAK | |
| L601 (success return 0) | success | YES (last child) | NO | ❌ LEAK | No of_node_put(child) |

**Pre‑Verdict Checklist:**
1. **"Held for device lifetime"?** Not applicable; the child node is only used during probe.
2. **"Ownership transferred"?** No. `child` is not stored in any long‑lived structure with documented cleanup.
3. **Unconditional GET?** `of_get_next_available_child()` unconditionally returns a node with a new reference — GET=YES on ALL paths after the call.
4. **goto out blocks?** No explicit goto, but error returns directly skip the needed `of_node_put(child)`.

Every error path after the first call to `of_get_next_available_child()` leaks the reference, and the final success return also leaks the last child reference. This is a **REAL_BUG** — refcount leak.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The probe function never calls of_node_put(child) on the device_node obtained via of_get_next_available_child(), leaking a reference on every error path inside and after the loop, and on the success return.
```
