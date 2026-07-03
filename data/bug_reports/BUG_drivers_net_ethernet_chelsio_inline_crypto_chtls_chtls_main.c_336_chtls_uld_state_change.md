# REAL BUG: drivers/net/ethernet/chelsio/inline_crypto/chtls/chtls_main.c:336 chtls_uld_state_change()

**Confidence**: HIGH | **Counter**: `cdev->tlsdev.kref.refcount.refs.counter`

## Reasoning

| default | return 0 | NO | NO | YES | no ops |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L321 (CXGB4_STATE_UP) | return 0 | YES (unconditional via `chtls_register_dev`) | NO | NO (leak in isolation) | GET not balanced in this call; intended to be released by future DETACH |
| L324 (CXGB4_STATE_DOWN) | return 0 | NO | NO | YES | no ops |
| L326 (CXGB4_STATE_START_RECOVERY) | return 0 | NO | NO | YES | no ops |
| L331 (CXGB4_STATE_DETACH) | return 0 | NO | YES (`kref_put`) | NO | PUT without prior GET; if `tlsdev.kref` never initialised (e.g., no prior UP) → refcount underflow |
| default | return 0 | NO | NO | YES | no ops |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Detach path unconditionally calls kref_put on cdev->tlsdev.kref without any check that the kref was previously initialised (via chtls_register_dev on CXGB4_STATE_UP). If DETACH occurs before any UP, the refcount is zero and kref_put triggers a refcount underflow ("excess put").
```
