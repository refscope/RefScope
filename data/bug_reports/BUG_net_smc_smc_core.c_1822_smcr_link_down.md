# REAL BUG: net/smc/smc_core.c:1822 smcr_link_down()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

cr_link_clear` called)** | `return` after `wake_up` | NO | **YES (switch put) + YES (`smcr_link_clear` put)** | **❌ EXCESS PUT** | `smc_switch_conns` already decremented lnk’s refcount (via `smc_switch_link_and_count(put)`); `smcr_link_clear` does an extra put, causing refcount underflow. |

## Full Response

```
## Path Table

| Line (approx) | Return Type | GET (increment on lnk?) Done? | PUT (decrement on lnk?) Done? | Balanced? | Notes |
|---------------|-------------|-------------------------------|-------------------------------|-----------|-------|
| L1792 (early guard) | `return` | NO | NO | ✅ | Guard before any reference operations. |
| L1800 (to_lnk == NULL) | `return` after `smcr_link_clear` | NO (no get from switch) | YES (`smcr_link_clear`) | ✅ | No backup link → no switch → no put from `smc_switch_conns`; explicit put is correct. |
| L~1810 (SMC_SERV, no clear) | implicit return at end of function | NO (switch does not get lnk) | YES (`smc_switch_conns` already put lnk) | ✅ | Successful switch already released lnk’s refcount; no extra put needed. |
| L~1830 (else branch, list_empty, no clear) | `return` after `wake_up` | NO | YES (`smc_switch_conns` already put lnk) | ✅ | List emptied, skip cleanup; switch already released refcount. |
| **L1822 (else branch, `smcr_link_clear` called)** | `return` after `wake_up` | NO | **YES (switch put) + YES (`smcr_link_clear` put)** | **❌ EXCESS PUT** | `smc_switch_conns` already decremented lnk’s refcount (via `smc_switch_link_and_count(put)`); `smcr_link_clear` does an extra put, causing refcount underflow. |

## PRE-VERDICT CHECKLIST

1. **“Held for device lifetime”?** → Not applicable; error paths are irrelevant.  
2. **“Ownership transferred”?** → No transfer of lnk; the role of smc_switch_conns is to move users away and put the old link. Cleanup is already done by the switch.  
3. **Unconditional GET?** → GET is conditional; the relevant operation here is the PUT inside `smc_switch_conns`, which is unconditional on the non‑NULL return path.  
4. **goto out between GET and PUT?** → No gotos; the dual‑put path is direct.

## Analysis

- The contract for `smc_switch_conns` includes both `smc_switch_link_and_count(get)` and `smc_switch_link_and_count(put)`.  
- The typical semantics of a switch operation is: the old link’s connections are moved, so its refcount is decremented (put), while the new link’s refcount is incremented (get).  
- Therefore, after a **successful** switch (non‑NULL `to_lnk`), `lnk`’s refcount has already been reduced by the `smc_switch_link_and_count(put)` inside `smc_switch_conns`.  
- The second call to `smcr_link_clear(lnk, true)` at line 1822 (SMC_CLNT path, list not empty) performs an **additional** decrement via `smcr_link_put`, hitting the refcount a second time and triggering the “refcount excess put” warning.  
- No early return, IS_ERR guard, or ownership transfer justifies the extra put on this path. The bug is a straightforward double‑put.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`smc_switch_conns` already drops `lnk`’s refcount on successful switch, making the subsequent `smcr_link_clear(lnk, true)` at line 1822 an excess put.
```
