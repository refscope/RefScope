# REAL BUG: net/batman-adv/bridge_loop_avoidance.c:2158 batadv_bla_tx()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

laim_put` (Line 2158) strongly suggests that on the timed‑out roaming branch it already released the claim reference. The subsequent `goto allow` leads to the common `out` label where `batadv_claim_put` is called again, triggering a double‑put / use‑after‑free.

## Full Response

```
| Line | Return Type | GET Done? (claim ref from hash_find) | PUT Done? (claim_put at out) | Balanced? | Notes |
|------|-------------|--------------------------------------|-----------------------------|-----------|-------|
| Primary if NULL → L2154 (out)  | ret false   | NO (claim NULL)                     | YES (NULL safe)            | ✅         | Early exit before claim lookup |
| bridge_loop_avoidance 0 → L2085 allow → out | ret false | NO (claim NULL)                     | YES (NULL safe)            | ✅         | |
| batadv_bla_process_claim true → L2088 handled → out | ret true | NO (claim NULL)                     | YES (NULL safe)            | ✅         | |
| num_requests & multicast → L2095 handled → out | ret true | NO (claim NULL)                     | YES (NULL safe)            | ✅         | |
| claim not found → L2104 allow → out | ret false | NO (hash_find returns NULL, GET failed) | YES (NULL safe)            | ✅         | |
| claim found, client_roamed & timed out: handle_unclaim → L2131 allow → out | ret false | YES (hash_find returned non‑NULL, reference taken) | YES but claim already put inside handle_unclaim → excess | ❌ EXCESS PUT | `batadv_handle_unclaim` likely calls `batadv_claim_put` internally, then we put again at `out` — flag by smatch. |
| claim found, client_roamed & not timed out → L2136 handled → out | ret true | YES | YES            | ✅         | Normal release |
| claim found, !client_roamed & multicast → L2145 handled → out | ret true | YES | YES            | ✅         | |
| claim found, !client_roamed & unicast → L2150 allow → out | ret false | YES | YES            | ✅         | |

⚠️ The `batadv_handle_unclaim` callee source is missing, but the “excess put” warning at the final `batadv_claim_put` (Line 2158) strongly suggests that on the timed‑out roaming branch it already released the claim reference. The subsequent `goto allow` leads to the common `out` label where `batadv_claim_put` is called again, triggering a double‑put / use‑after‑free.

[NEED_SOURCE] batadv_handle_unclaim

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`batadv_handle_unclaim` on the roaming‑timed‑out path drops the claim reference, but the code then executes `batadv_claim_put(claim)` at the shared `out` label, causing an excess put (refcount already zero → double‑free). The claim pointer must be NULL’d or the path must avoid the final put.
```
