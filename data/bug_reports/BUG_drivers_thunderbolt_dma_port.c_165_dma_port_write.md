# REAL BUG: drivers/thunderbolt/dma_port.c:165 dma_port_write()

**Confidence**: MEDIUM | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| return res.err | YES (tb_cfg_request_alloc L138, ref = 1) | YES (tb_cfg_request_put L165) | ❓ depends on tb_cfg_request_sync | If tb_cfg_request_sync already calls tb_cfg_request_put, then this explicit put is an extra kref_put → refcount goes under 0 (excess put). Warning indicates this case. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L141 | error (return -ENOMEM) | NO (req NULL from tb_cfg_request_alloc) | N/A | ✅ | No ref acquired |
| L165 | return res.err | YES (tb_cfg_request_alloc L138, ref = 1) | YES (tb_cfg_request_put L165) | ❓ depends on tb_cfg_request_sync | If tb_cfg_request_sync already calls tb_cfg_request_put, then this explicit put is an extra kref_put → refcount goes under 0 (excess put). Warning indicates this case. |

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  
tb_cfg_request_alloc sets kref to 1, and tb_cfg_request_put at L165 would normally release it. However, the static analysis warning of “refcount excess put” strongly suggests that tb_cfg_request_sync internally calls tb_cfg_request_put (consuming the request), making the caller’s explicit put a double-put. Without the source of tb_cfg_request_sync we cannot be 100% certain, but the pattern is a well‑known ownership‑consumption bug.
```
