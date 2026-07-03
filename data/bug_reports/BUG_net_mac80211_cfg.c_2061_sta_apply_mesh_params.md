# REAL BUG: net/mac80211/cfg.c:2061 sta_apply_mesh_params()

**Confidence**: HIGH | **Counter**: `$->u.mesh.estab_plinks.counter`

## Reasoning

PLINK_ESTAB)` ensures the dec only occurs when the station is in ESTAB state, but the refcount could be zero if the ESTAB state was ever set without a matching `mesh_plink_inc_estab_count()`. This is a classic cross‑call imbalance: a missing increment elsewhere causes an observable underflow here.

## Full Response

```
| Line | Return Type | GET Done? (inc) | PUT Done? (dec) | Balanced? | Notes |
|------|-------------|-----------------|-----------------|-----------|-------|
| Function end (void return) | void     | Depends: yes (ESTAB transition from non‑ESTAB), else no | Depends: yes (non‑ESTAB transition from ESTAB), else no | N/A – global counter update | No in‑function resource leak; the warning is about a *cross‑call* imbalance: the dec at ~L2061 ran with counter already zero, implying a missing inc. |
| ESTAB case with plink_state != ESTAB | (inside function) | YES (inc_estab_count) | NO | – | Inc path |
| Non‑ESTAB case with plink_state == ESTAB | (inside function) | NO | YES (dec_estab_count) | – | Dec path – this is the line that triggers the excess‑put warning if estab_plinks was 0. |

The function contains no early returns or error paths – it’s a void state‑transition handler. The `refcount excess put` at line 2061 is the call to `mesh_plink_dec_estab_count()`. The guard `if (sta->mesh->plink_state == NL80211_PLINK_ESTAB)` ensures the dec only occurs when the station is in ESTAB state, but the refcount could be zero if the ESTAB state was ever set without a matching `mesh_plink_inc_estab_count()`. This is a classic cross‑call imbalance: a missing increment elsewhere causes an observable underflow here.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH
```
