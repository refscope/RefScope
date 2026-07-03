# REAL BUG: drivers/net/ethernet/mediatek/mtk_eth_soc.c:4478 mtk_pending_work()

**Confidence**: HIGH | **Counter**: `(r netdev_priv($))->hw->dma_refcnt.refs.counter`

## Reasoning

| L4436, L4451 (mtk_open succeeds) | void exit (function end) | YES (mtk_open inc) | YES (mtk_stop at L4436) | ✅ | PUT then GET, net zero change from initial up state |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L4436, L4451-L4454 (mtk_open fails) | void exit (function end) | NO (mtk_open conditional, failed → no inc) | YES (mtk_stop via dev_close at L4454) + earlier mtk_stop at L4436 | ❌ EXCESS PUT | L4436 put zeroes refcount; dev_close calls mtk_stop again on a zero refcount → underflow |
| L4436, L4451 (mtk_open succeeds) | void exit (function end) | YES (mtk_open inc) | YES (mtk_stop at L4436) | ✅ | PUT then GET, net zero change from initial up state |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
In the restart loop, when mtk_open fails, the subsequent dev_close issues a second unbalanced mtk_stop after an earlier stop already zeroed the refcount, causing the reported excess put/underflow on dma_refcnt.
```
