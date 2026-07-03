# REAL BUG: drivers/gpu/drm/amd/amdgpu/../display/dc/core/dc.c:4959 commit_minimal_transition_based_on_current_context()

**Confidence**: MEDIUM | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

om swap_and_release_current_context (L4932) and release_minimal_transition_state | ❌ likely EXCESS | Extra decrements before L4937 trigger "excess put" warning at L4937. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L4937 (end) | return false (intermediate NULL) | YES (dc_state_retain at L4919) | YES (dc_state_release at L4937) | ✅ | One retain, one release. Balanced if release_minimal_transition_state not called. |
| L4937 (end) | return false/true (intermediate != NULL, seamless false) | YES (L4919) | YES? (dc_state_release at L4937) | ⚠️ Possibly ❌ LEAK/EXCESS? | release_minimal_transition_state at L4935 might also PUT old_current_state. If it does, two PUTs → excess on L4937. |
| L4937 (end) | return true (intermediate != NULL, seamless true)   | YES (L4919) | YES? (dc_state_release) + possible extra from swap_and_release_current_context (L4932) and release_minimal_transition_state | ❌ likely EXCESS | Extra decrements before L4937 trigger "excess put" warning at L4937. |

**Request**: `[NEED_SOURCE] release_minimal_transition_state`  
**Request**: `[NEED_SOURCE] swap_and_release_current_context`

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
dc_state_retain unconditionally increments old_current_state’s refcount. The warning of an excess put at dc_state_release (L4959) implies that old_current_state was already released an extra time before that final put. In the non‑NULL intermediate path, release_minimal_transition_state (unconditional put contract) likely decrements the refcount on old_current_state (or swap_and_release_current_context does so), causing a double‑release when the later dc_state_release runs. The exact culprit depends on the callee internals, but the pattern points to a real refcount imbalance.
```
