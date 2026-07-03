# REAL BUG: drivers/cdx/controller/mcdi.c:510 cdx_mcdi_rpc_sync()

**Confidence**: HIGH | **Counter**: `$->refcount.refs.counter`

## Reasoning

| L505‑506 (out, success/timeout) | return from success/timeout | YES: both inits + get on wait_data | wait_data: final put at L505. cmd_item: released by async machinery thereafter | ✅ (external) | cmd_item put happens via completer/cancel; balanced overall |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L458 | early error | NO (no init) | N/A | ✅ | before any allocation |
| L462 | early error | NO (no init) | N/A | ✅ | before kref_init on wait_data |
| L479‑481 (goto out) | error from cdx_mcdi_rpc_async_internal | YES: wait_data (kref_init + kref_get), cmd_item (kref_init) | wait_data: one put at L480 + final put at L505. cmd_item: **NO** | ❌ LEAK for cmd_item | cmd_item ref=1 from kref_init, never released; async_internal failed ⇒ no ownership transfer |
| L505‑506 (out, success/timeout) | return from success/timeout | YES: both inits + get on wait_data | wait_data: final put at L505. cmd_item: released by async machinery thereafter | ✅ (external) | cmd_item put happens via completer/cancel; balanced overall |

VERDICT: REAL_BUG

CONFIDENCE: HIGH

`cdx_mcdi_rpc_async_internal` error path leaks the `kref_init` reference on `cmd_item`, which is never released on that path.
```
