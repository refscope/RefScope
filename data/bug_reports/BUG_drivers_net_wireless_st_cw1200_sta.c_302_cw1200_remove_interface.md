# REAL BUG: drivers/net/wireless/st/cw1200/sta.c:302 cw1200_remove_interface()

**Confidence**: HIGH | **Counter**: `$->tx_lock.counter`

## Reasoning

| L268–278 (AP), L279 (MONITOR), default (passive) – any | no lock taken; flush=0 → unlock at L301 | NO | YES (L301) | ❌ EXCESS | unlock without prior lock → excess put |

## Full Response

```
| Line(s) | Path Description | GET Done? | PUT Done? | Balanced? | Notes |
|---------|------------------|-----------|-----------|-----------|-------|
| L261–264 (join_status STA etc.) + L301 | queue_work returns ≤0 → immediate unlock (L264), later __cw1200_flush returns 0 → unlock again (L301) | YES (L261) | YES (L264) + YES (L301) | ❌ EXCESS | double unlock leads to “refcount excess put” |
| L261–264 (join_status STA etc.) + L301 | queue_work ≤0 (unlock at L264), flush !=0 → no second unlock | YES (L261) | YES (L264) only | ✅ | lock released once, no extra put |
| L261–264 (join_status STA etc.) + L301 | queue_work >0 (no immediate unlock), flush =0 → unlock at L301 | YES (L261) | YES (L301) only | ✅ | single unlock after work queued |
| L261–264 (join_status STA etc.) + L301 | queue_work >0, flush !=0 → never unlocked | YES (L261) | NO | ❌ LEAK | lock held but never released |
| L268–278 (AP), L279 (MONITOR), default (passive) – any | no lock taken; flush=0 → unlock at L301 | NO | YES (L301) | ❌ EXCESS | unlock without prior lock → excess put |
| L268–278 (AP), L279 (MONITOR), default (passive) – any | no lock taken; flush !=0 → no unlock | NO | NO | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`wsm_lock_tx`/`wsm_unlock_tx` pairing is broken: in STA/IBSS join path a failed `queue_work` triggers an immediate unlock (L264), yet the later `!__cw1200_flush` path (L301) can call `wsm_unlock_tx` again, causing the reported excess put.
```
