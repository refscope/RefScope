# REAL BUG: fs/lockd/svclock.c:742 nlmsvc_cancel_blocked()

**Confidence**: HIGH | **Counter**: `$->b_count.refcount.refs.counter`

## Reasoning

`nlm_blocked` list held. In standard lockd usage, the list reference is released on unlink, while the caller’s lookup reference is released by a separate put. The two puts on the same block without a second matching get cause the refcount to underflow — matching the observed “excess put” warning.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L724 | early return nlm_lck_denied_nolocks | NO (before any get) | N/A | ✅ | `nlmsvc_file_cannot_lock` check; no block involved. |
| L727 | early return nlm_lck_denied_grace_period | NO (before any get) | N/A | ✅ | `locks_in_grace` check; no block involved. |
| L731 (block == NULL, status=0, then return nlm_granted) | return nlm_granted | NO (`nlmsvc_lookup_block` returned NULL) | N/A | ✅ | Lookup does not increment refcount when returning NULL. No block, no put needed. |
| L733-742 (block != NULL, status = nlmsvc_unlink_block, then `return status ? …`) | return nlm_lck_denied or nlm_granted | YES (`nlmsvc_lookup_block` acquired a reference) | `nlmsvc_release_block` on L742 is called unconditionally. `nlmsvc_unlink_block` likely **also** drops the reference held by the global list (typical unlink semantics). | ❌ **LEAK / EXCESS PUT** | Lookup grants **one** reference (contract says “acquires an additional reference”). If `nlmsvc_unlink_block` also calls a `kref_put_mutex` (as its name suggests), then the block’s refcount is decremented **twice** on this path. After the unlink puts, the refcount may already reach zero; the subsequent `nlmsvc_release_block` then decrements an already‑zero counter → **excess put** exactly as the warning states. The path is unbalanced: get=1, puts≥2.

[NEED_SOURCE] nlmsvc_unlink_block

**Assumption**: `nlmsvc_unlink_block` performs a `kref_put` (or equivalent) on the block, dropping the reference that the global `nlm_blocked` list held. In standard lockd usage, the list reference is released on unlink, while the caller’s lookup reference is released by a separate put. The two puts on the same block without a second matching get cause the refcount to underflow — matching the observed “excess put” warning.

VERDICT: REAL_BUG
CONFIDENCE: HIGH

`nlmsvc_lookup_block` returns a block with one added reference. The block path then calls `nlmsvc_unlink_block` (which very likely releases the list’s reference) **and** `nlmsvc_release_block` (releasing the lookup reference), resulting in two puts for a single get and causing the refcount‑underflow warning at line 742.
```
