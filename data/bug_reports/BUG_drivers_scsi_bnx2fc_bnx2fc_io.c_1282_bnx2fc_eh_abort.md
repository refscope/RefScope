# REAL BUG: drivers/scsi/bnx2fc/bnx2fc_io.c:1282 bnx2fc_eh_abort()

**Confidence**: LOW | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| L1277→done (fallthrough) | implicit, via done | YES | YES (done’s put + L1276 SCSI put) | ✅ | successful abort; eh_abort and SCSI references released separately, no excess |

## Full Response

```
| Line | Return Type | GET Done? (kref_get at L1160) | PUT Done? (matching eh_abort ref) | Balanced? | Notes |
|------|-------------|-------------------------------|-----------------------------------|-----------|-------|
| L1136 | error return rc | NO (before get) | N/A | ✅ | fc_block_scsi_eh check, no ref taken |
| L1141 | return FAILED | NO (before get) | N/A | ✅ | link not ready, no ref taken |
| L1154 | return SUCCESS | NO (io_req NULL) | N/A | ✅ | kref_get not reached |
| L1175 | return SUCCESS | YES | YES (kref_put at L1173) | ✅ | flush_in_prog path, explicitly released |
| L1186 | return FAILED | YES | NO ❌ | ❌ LEAK | on_active_queue==0, forgot kref_put; leak (not the excess‑put warning) |
| **L1223** (goto done) | goto done → eventual return at L1282 | **YES** | **YES (done’s put at L1280) + bnx2fc_abts_cleanup’s put** | **❌ EXCESS PUT** | ISSUE_ABTS set: we call `bnx2fc_abts_cleanup(io_req)` (contract: unconditional kref_put) **without** a matching `bnx2fc_initiate_abts()` get; then `kref_put` at done releases the eh_abort reference → one extra decrement → refcount underflow |
| L1240 (goto done) | goto done | YES | YES (done’s put) | ✅ | bnx2fc_initiate_abts failed; cleanup via bnx2fc_initiate_cleanup (no extra put known) |
| L1266 (goto done) | goto done | YES | YES (done’s put + bnx2fc_abts_cleanup matches initiate_abts get) | ✅ | abort failed path; balanced |
| L1277→done (fallthrough) | implicit, via done | YES | YES (done’s put + L1276 SCSI put) | ✅ | successful abort; eh_abort and SCSI references released separately, no excess |

**VERDICT:** REAL_BUG  
**CONFIDENCE:** HIGH  
In the `test_and_set_bit(BNX2FC_FLAG_ISSUE_ABTS)` path (line 1204), `bnx2fc_abts_cleanup()` performs a kref_put that corresponds to the reference normally taken by `bnx2fc_initiate_abts()`, but `bnx2fc_initiate_abts()` is **not called** in that block. Combined with the `done` label’s kref_put for the eh_abort reference, this results in an extra kref_put, causing a refcount underflow (excess put). The leak on L1186 is a separate bug.
```
