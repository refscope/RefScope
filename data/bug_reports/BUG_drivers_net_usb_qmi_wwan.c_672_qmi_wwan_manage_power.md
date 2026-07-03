# REAL BUG: drivers/net/usb/qmi_wwan.c:672 qmi_wwan_manage_power()

**Confidence**: HIGH | **Counter**: `info->pmcount.counter`

## Reasoning

| L668 | return 0 (on=0, pmcount 0→-1, condition false) | NO | YES (dec) | **NO ❌** | Unconditional decrement when counter already zero → underflow → excess put |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L668 | return 0 (on=1, pmcount 0→1, condition true) | YES (+1) | N/A | N/A | Not a put path; fine for "on" semantics |
| L668 | return 0 (on=1, pmcount >0→>1, condition false) | YES (+1) | N/A | N/A | Not a put path; fine |
| L668 | return 0 (on=0, pmcount 1→0, condition true) | NO | YES (dec) | YES | Decrements from 1 to 0; balanced |
| L668 | return 0 (on=0, pmcount >1→>0, condition false) | NO | YES (dec) | YES | Normal decrement, still >0; balanced |
| L668 | return 0 (on=0, pmcount 0→-1, condition false) | NO | YES (dec) | **NO ❌** | Unconditional decrement when counter already zero → underflow → excess put |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`atomic_dec_and_test` is called unconditionally on `on=0`, but if `pmcount` is already 0 the decrement underflows (excess put); no guard against zero before the operation.
```
