# REAL BUG: drivers/net/wireless/st/cw1200/sta.c:436 cw1200_config()

**Confidence**: LOW | **Counter**: `$->tx_lock.counter`

## Reasoning

ock’s flush (“implicitly locks tx”) and explicit unlock only on failure strongly suggests `__cw1200_flush` / `wsm_lock_tx` are refcount‑based locks. The absence of any return‑value check before `wsm_unlock_tx` in the IDLE block makes an excess put **very likely** when the lock acquisition fails.

## Full Response

```
[NEED_SOURCE] wsm_lock_tx
[NEED_SOURCE] wsm_unlock_tx
[NEED_SOURCE] __cw1200_flush

## Path Table

| Line (approx.) | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|----------------|-------------|-----------|-----------|-----------|-------|
| L436 (no IDLE/CHANNEL) | success     | NO (no lock calls) | NO  | ✅ | |
| L436 (CHANNEL: flush fails) | success | NO                | NO  | ✅ | |
| L436 (CHANNEL: flush OK, switch fails) | success | YES (from flush) | YES (explicit unlock) | ✅ | |
| L436 (CHANNEL: flush OK, switch OK, wait timeout) | success | YES | NO  | ❌ LEAK (missing unlock) | No `wsm_unlock_tx` |
| L436 (CHANNEL: flush OK, switch OK, wait success) | success | YES | YES (comment: “Already unlocks”) | ✅ | |
| L436 (IDLE block executed, `wsm_lock_tx` **succeeds**) | success | YES | YES | ✅ | |
| L436 (IDLE block executed, `wsm_lock_tx` **fails** – contract unknown) | success | NO (if conditional) | YES | ⚠️ Excess put | Unlock without lock |

The function has a single return at L436. The table enumerates all distinct lock/unlock scenarios that reach that return. The `IDLE` block always calls `wsm_lock_tx(priv)` (ignoring any return) and later `wsm_unlock_tx(priv)`. If `wsm_lock_tx` is a **conditional** acquire (e.g., try‑lock or `kref_get_unless_zero`‑style) and fails, the subsequent `wsm_unlock_tx` becomes an unmatched release, leading to a refcount underflow. The warning “refcount excess put” exactly matches this pattern.

Because the contracts for `wsm_lock_tx` / `wsm_unlock_tx` are unknown, the exact semantics are uncertain. However, the code’s comment for the CHANNEL block’s flush (“implicitly locks tx”) and explicit unlock only on failure strongly suggests `__cw1200_flush` / `wsm_lock_tx` are refcount‑based locks. The absence of any return‑value check before `wsm_unlock_tx` in the IDLE block makes an excess put **very likely** when the lock acquisition fails.

**VERDICT: REAL_BUG**
**CONFIDENCE: LOW**
`cw1200_config()` calls `wsm_unlock_tx()` unconditionally after `wsm_lock_tx()` in the IDLE block without checking whether the lock was actually acquired; if `wsm_lock_tx` can fail (conditional get), this results in an excess put / refcount underflow.
```
