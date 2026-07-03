# REAL BUG: net/ipv6/addrconf.c:4298 addrconf_dad_work()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| L4276‑4283 (dad_probes>0) | fallthrough to out | Unknown (conditional `addrconf_mod_dad_work`) | YES (out put) + possibly PUT from mod_dad_work | ❓ | Exact balance depends on mod_dad_work semantics, but the clearest bug is the success path above. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L4233 (DAD_BEGIN) | goto out | NO (no explicit get) | YES (out put) | ✅ | Implicit work ref balanced by out put; no extra get/put. |
| L4242 (DAD_ABORT) | goto out | YES (in6_ifa_hold) + YES (addrconf_dad_stop's hold) → 2 | YES (addrconf_dad_stop's put) + YES (out put) → 2 | ✅ | Per contract, stop does a get and a put → balanced with hold and final put. |
| L4244 (dad_end) | goto out | NO | YES (out put) | ✅ | Only out put vs. implicit work ref. |
| L4248 (idev dead) | goto out | NO | YES (out put) | ✅ | Same. |
| L4254 (state DEAD) | goto out | NO | YES (out put) | ✅ | Same. |
| L4262‑4274 (dad_probes==0) | goto out | NO (no get) | YES (addrconf_dad_completed’s put) + YES (out put) → 2 PUTs | ❌ | **Double put:** `addrconf_dad_completed` does a put (contract says unconditional), then out does another. Only one implicit work ref exists → excess put → real bug. |
| L4276‑4283 (dad_probes>0) | fallthrough to out | Unknown (conditional `addrconf_mod_dad_work`) | YES (out put) + possibly PUT from mod_dad_work | ❓ | Exact balance depends on mod_dad_work semantics, but the clearest bug is the success path above. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The success path (dad_probes == 0) unconditionally calls `addrconf_dad_completed`, which per contract does an `in6_ifa_put`, then jumps to `out` and does another `in6_ifa_put`; with only one implicit work reference held this results in an excess put.
```
