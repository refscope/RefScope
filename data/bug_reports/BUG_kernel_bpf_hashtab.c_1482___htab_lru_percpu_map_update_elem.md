# REAL BUG: kernel/bpf/hashtab.c:1482 __htab_lru_percpu_map_update_elem()

**Confidence**: HIGH | **Counter**: `*htab->map.elem_count`

## Reasoning

ps an element from the pre‑allocated free list **without** incrementing the in‑use element count, because the count is preset at map creation. The warning “excess put” confirms that smatch sees a dec without a matching inc. Therefore the error and `l_old` paths are an **excess put** (underflow).

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1431 | error       | NO (before get) | N/A | ✅ | early `htab_map_check_update_flags` failure |
| L1445 | error       | NO (get failed) | N/A | ✅ | `prealloc_lru_pop` returned NULL, no `l_new` |
| L1450 | goto `err_lock_bucket` | YES (prealloc_lru_pop succeeded) | YES | ❌ EXCESS PUT | `l_new` valid → `bpf_map_dec_elem_count` called |
| L1456 | goto `err` | YES | YES | ❌ EXCESS PUT | `check_flags` failure → fall through to same put block |
| L1461‑L1465 (l_old path) | success with existing elem | YES | YES | ❌ EXCESS PUT | `l_new` not used, falls through to put on exit |
| L1461‑L1464 (l_new used) | success, `l_new = NULL` | YES (then cleared) | NO | ✅ | ownership transferred to hash, no put needed |

**Rationale:**  
The function `__htab_lru_percpu_map_update_elem` allocates a new LRU element via `prealloc_lru_pop` when `map_flags != BPF_EXIST`. On **every** path where `l_new` remains non‑NULL (both explicit errors and the `l_old` success path), the code calls `bpf_map_dec_elem_count`. This decrement is **only correct** if `prealloc_lru_pop` had previously incremented the map’s `elem_count`. For a **pre‑allocated** LRU map, `prealloc_lru_pop` typically pops an element from the pre‑allocated free list **without** incrementing the in‑use element count, because the count is preset at map creation. The warning “excess put” confirms that smatch sees a dec without a matching inc. Therefore the error and `l_old` paths are an **excess put** (underflow).

**VERDICT: REAL_BUG**  
**CONFIDENCE: HIGH**
```
