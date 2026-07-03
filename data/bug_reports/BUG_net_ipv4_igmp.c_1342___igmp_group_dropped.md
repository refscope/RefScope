# REAL BUG: net/ipv4/igmp.c:1342 __igmp_group_dropped()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| L1343 (fallthrough, IGMPv3) | return (implicit end) | YES (igmpv3_add_delrec) | NO | ⚠️ LEAK? | gets released later via igmpv3_del_delrec — not involved in excess put |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1323 | return (IGMP_ALL_HOSTS) | NO (before any get) | NO (before igmp_stop_timer) | ✅ |  |
| L1325 | return (local multicast, sysctl) | NO | NO | ✅ |  |
| L1332 | return (IGMP V1) | NO | YES (igmp_stop_timer called) | ❌ EXCESS PUT | igmp_stop_timer may dec ref even if no timer ref held |
| L1336 | return (IGMP V2) | NO | YES | ❌ EXCESS PUT | same as above |
| L1343 (fallthrough, in_dev dead) | return (implicit end) | NO | YES | ❌ EXCESS PUT | stop_timer called; if device dead, reference may be stale |
| L1343 (fallthrough, IGMPv3) | return (implicit end) | YES (igmpv3_add_delrec) | NO | ⚠️ LEAK? | gets released later via igmpv3_del_delrec — not involved in excess put |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On multiple paths, `igmp_stop_timer()` (a put) is invoked without any preceding get in this function; if the timer was never started and no reference exists, this causes the refcount underflow seen at line 1342.
```
