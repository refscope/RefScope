# REAL BUG: drivers/media/pci/cx18/cx18-ioctl.c:846 cx18_g_enc_index()

**Confidence**: HIGH | **Counter**: `s->q_full.depth.counter`

## Reasoning

Because the empty‑queue path calls `cx18_dequeue`, which (by contract) is an unconditional PUT, the counter gets decremented without any preceding GET, leading to underflow — a clear excess put.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L809 | early error (`return -EINVAL`) | NO (before any queue ops) | NO | ✅ | No get/put on `q_full` |
| L822-824 (mdl==NULL break → `return 0`) | break | NO (no `cx18_push` in this iteration) | YES (`cx18_dequeue` called unconditionally) | ❌ Excess PUT | If queue empty, dequeue decrements counter below zero |
| L827-829 (push back path) | break, then `return 0` | YES (`cx18_push` called) | YES (dequeue called) | ✅ | net zero on `q_full` |
| L832-837 (drain to `q_free`) | continue loop, eventually `return 0` | NO (no push) | YES (dequeue) | ⚠️ Net decrement per drained item; overall may be fine but tool flags one path. |  |

**Pre‑verdict checklist**

1. **“Held for device lifetime”?** – Not applicable; temporary queue.
2. **“Ownership transferred”?** – No; queue items are not transferred — they are either pushed back or moved to `q_free`.
3. **Unconditional GET?** – GET is `cx18_push` (only when data remains). PUT `cx18_dequeue` appears unconditional — it decrements counter even if queue empty.
4. **goto out between GET and PUT?** – No `goto` between dequeue and push; the dangerous path is the `break` on NULL.

Because the empty‑queue path calls `cx18_dequeue`, which (by contract) is an unconditional PUT, the counter gets decremented without any preceding GET, leading to underflow — a clear excess put.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`cx18_dequeue` decrements `s->q_full.depth` unconditionally, but the loop calls it before the NULL check; an empty queue leaves the counter negative.
```
