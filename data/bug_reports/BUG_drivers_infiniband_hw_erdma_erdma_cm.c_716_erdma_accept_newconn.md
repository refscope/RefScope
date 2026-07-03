# REAL BUG: drivers/infiniband/hw/erdma/erdma_cm.c:716 erdma_accept_newconn()

**Confidence**: MEDIUM | **Counter**: `$->ref.refcount.refs.counter`

## Reasoning

No other path can produce an excess put because all other fail points either never allocate, have only one ref to drop, or release exactly the three references via the combination of cancel, disassoc, and the final put.

## Full Response

```
## Enumerated Return Paths

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L648 (goto error) | error | NO (before any get on new_cep, new_cep is NULL) | N/A | ✅ | cep->state check fails. |
| L653 (goto error) | error | NO (erdma_cep_alloc returned NULL) | N/A | ✅ | new_cep is NULL. |
| L660 (goto error) | error | YES (alloc → 1 ref) | YES (cancel mpatimer no‑op, put at L716) | ✅ | Single ref dropped to 0. |
| L671 (goto error) | error | YES (alloc → 1 ref) | YES (cancel no‑op, put at L716) | ✅ | kernel_accept failed, no extra gets. |
| L681 (goto error) | error | YES (alloc + L674 get + queue_work get = 3 refs) | YES (cancel timer drops 1, disassoc drops socket ref, put drops 1 → total 3) | ✅ | All sources of refcount balanced here. |
| L695 (goto error after erdma_proc_mpareq error) | error | YES (alloc + L674 + queue_work = 3 refs, plus any get from erdma_proc_mpareq) | YES (cancel timer, disassoc, put at L716) | ❌ EXCESS PUT | If erdma_proc_mpareq on error already called erdma_cep_put(new_cep) (contract says conditional put/get), then the error label’s subsequent cancel + put will cause a double put → refcount underflow. The smatch warning pinpoints line 716 as the site of excess put. |
| L702 (return) | success | YES (multiple gets held by socket/timer) | NO (ownership transferred to socket/timer) | ⚠️ Acceptable | No local put – references are held by the socket (sk_user_data) and the deferred timer work. |

## Contract‑Driven Reasoning

- The **unconditional** `erdma_cep_get()` on L674 and the **unconditional** get inside `erdma_cm_queue_work()` (L679) add two references beyond the initial alloc.
- On the error path that enters the `erdma_proc_mpareq` block (L686‑701), if `ret != -EAGAIN` and `ret != 0` we fall through to `goto error`.  
  At that point the total refcount on `new_cep` is **3 + any get/put that `erdma_proc_mpareq` performed**.
- The **error label** unconditionally calls `erdma_cancel_mpatimer()` (may put if timer was active) and then `erdma_cep_put()`.
- If `erdma_proc_mpareq` on error **already releases a reference** (which its contract says is possible: “conditional_on_path; →erdma_cep_put(put)”), then the error label’s extra put at **line 716** becomes a **double put**, driving the refcount below zero – exactly the “refcount excess put” observed.

No other path can produce an excess put because all other fail points either never allocate, have only one ref to drop, or release exactly the three references via the combination of cancel, disassoc, and the final put.

## Verdict

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  

One-liner: `erdma_proc_mpareq()` likely drops a reference on error, but the caller’s error path also does `erdma_cep_put()` at line 716, causing a double put and refcount underflow.
```
