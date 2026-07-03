# REAL BUG: net/sctp/input.c:452 sctp_icmp_proto_unreachable()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| L452 (else branch: timer_delete returns false) | function end | NO | NO | ✅ | No timer pending, no put. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L436 (return in sock_owned_by_user, timer pending) | early return | NO (no GET) | NO (no PUT) | ✅ | No GET, no PUT. |
| L440 (implicit function end after mod_timer fails, hold called) | function end | YES (hold called, but **conditional**; success=YES, fail=NO) | NO (no PUT) | ⚠️ Pending: hold may fail | If hold fails (returns 0), GET=NO; timer armed anyway → pending timer without ref. If hold succeeds, balanced for this arm. |
| L440 (implicit function end after mod_timer succeeds) | function end | NO (no hold called) | NO (no PUT) | ✅ | Timer already pending; no extra hold, so no put needed. |
| L452 (else branch: timer_delete returns true → put) | function end (after sctp_do_sm) | NO (no GET in else branch) | YES (put called) | ❌ EXCESS: PUT without a corresponding GET if hold failed in the deferred path | The else branch only puts if the timer was pending. If the deferred path armed the timer but hold failed, here we get an unmatched put. |
| L452 (else branch: timer_delete returns false) | function end | NO | NO | ✅ | No timer pending, no put. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
sctp_transport_hold may fail (return 0) if the transport is already dead, but the deferred path still arms the timer via mod_timer. Later, the else branch deletes the timer and unconditionally puts, even though no reference was held.
```
