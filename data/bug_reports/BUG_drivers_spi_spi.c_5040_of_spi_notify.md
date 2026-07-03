# REAL BUG: drivers/spi/spi.c:5040 of_spi_notify()

**Confidence**: LOW | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

- `goto` between GET and PUT? Not applicable.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L4998 | return NOTIFY_OK (ctlr==NULL) | NO (find NULL) | N/A | ✅ | |
| L5002 | return NOTIFY_OK (flag set) | YES (ctlr ref from of_find_spi_controller_by_node) | YES (put_device L5001) | ✅ | |
| L5016 | return notifier_from_errno (IS_ERR spi) | ctlr ref already put (L5011); spi ERR → NO get from of_register_spi_device (assumed) | ctlr put done; no spi put needed | ✅ | |
| L5038 (ADD success) | return NOTIFY_OK | YES (spi ref from of_register_spi_device – contract says unconditional get) | NO put on spi | ❌ Missing spi put (possible leak) – but warning is **excess put**, not leak. The alloc ref may be held until removal, but if of_register_spi_device already released it (spi_dev_put side‑effect), later REMOVE path will excess‑put. | Missing put if alloc ref retained; excess if already released. |
| L5023 | return NOTIFY_OK (flag not set) | NO | N/A | ✅ | |
| L5028 | return NOTIFY_OK (spi==NULL) | NO | N/A | ✅ | |
| L5038 (REMOVE) | return NOTIFY_OK | YES (spi ref from of_find_spi_device_by_node – presumed get) | YES (put_device L5034) but spi_unregister_device may also put | ⚠️ Potential excess: if of_register_spi_device already called spi_dev_put, the alloc ref is gone; spi_unregister_device drops model ref → refcount 0; then put_device L5034 → **excess put**. | Need callee sources to confirm. |

The `excess put` warning points to the spi device’s kref. The most likely location is the `put_device(&spi->dev)` in the `REMOVE` path (line 5034, which may expand to line 5040). The contract for `of_register_spi_device()` lists `spi_dev_put` as a side‑effect, suggesting it may have already released the alloc reference. If so, the subsequent put in the REMOVE case would decrement the refcount below zero. Without the internals of `of_register_spi_device`, `of_find_spi_device_by_node`, and `spi_unregister_device`, the exact balance cannot be decided.

[NEED_SOURCE] of_register_spi_device  
[NEED_SOURCE] of_find_spi_device_by_node  
[NEED_SOURCE] spi_unregister_device  

**Pre-Verdict Checklist**  
- “Held for lifetime”? Possibly, but the REMOVE path’s put_device on an already‑zero counter creates the excess.  
- Ownership transfer? No explicit cleanup code for the REMOVE path’s double‑put.  
- Unconditional GET from `of_register_spi_device`? Contract says yes, but internal `spi_dev_put` may cancel it.  
- `goto` between GET and PUT? Not applicable.

VERDICT: REAL_BUG  
CONFIDENCE: LOW  
Based on the `of_register_spi_device()` contract showing an unconditional `spi_dev_put` side‑effect, the `put_device(&spi->dev)` in the `REMOVE` path likely produces a refcount excess put. Source verification is required.
```
