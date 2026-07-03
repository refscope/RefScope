# REAL BUG: drivers/tty/tty_jobctrl.c:238 tty_signal_session_leader()

**Confidence**: HIGH | **Counter**: `$->count.refs.counter`

## Reasoning

| L235 (leader, `tty->ctrl.pgrp == NULL`) | success | YES (tty_pgrp) | YES (old pgrp put) | ❌ DANGER | `put_pid(old)` followed by **no** new assignment → dangling pointer; subsequent calls will put an already‑released pid → refcount underflow (excess put) |

## Full Response

```
## Path Table

| Line | Return Type | GET Done? (tty_pgrp) | PUT Done? (tty_pgrp) | Balanced? | Notes |
|------|-------------|---------------------|---------------------|-----------|-------|
| L235 (if `tty->ctrl.session` is NULL) | success | NO | NO | ✅ | Skip loop, tty_pgrp=NULL |
| L235 (if session non‑NULL but no leader found) | success | NO | NO | ✅ | All tasks fail `!p->signal->leader`, continue early |
| L235 (single leader) | success | YES (1 get) | YES (1 put) | ✅ | tty_pgrp balanced |
| L235 (multiple leaders) | success | YES (N gets) | YES (1 put) | ❌ LEAK | tty_pgrp overwritten N‑1 times without put |
| L235 (leader, `tty->ctrl.pgrp != NULL`) | success | YES (tty_pgrp + new old pgrp) | YES (old pgrp put) | ✅ | Old pgrp replaced correctly |
| L235 (leader, `tty->ctrl.pgrp == NULL`) | success | YES (tty_pgrp) | YES (old pgrp put) | ❌ DANGER | `put_pid(old)` followed by **no** new assignment → dangling pointer; subsequent calls will put an already‑released pid → refcount underflow (excess put) |

**VERDICT: REAL_BUG**
**CONFIDENCE: HIGH**
On the path where `tty->ctrl.pgrp` is NULL, `put_pid(p->signal->tty_old_pgrp)` releases the old pid but leaves the pointer unchanged; the next invocation will call `put_pid` on a freed pid with refcount 0, causing the observed excess put.
```
