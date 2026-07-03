# REAL BUG: drivers/scsi/libsas/sas_expander.c:965 sas_ex_discover_expander()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| ~L965 | return child (success) | YES (initial ref) | sas_discover_expander may have done a get+put (net zero); no extra put | ✅ | caller holds the returned reference; no extra put on this path |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L898 | NULL (phy routing) | NO (before alloc) | N/A | ✅ | |
| ~L906 | NULL (alloc fail) | NO (child is NULL) | N/A | ✅ | |
| ~L962 | NULL (error after sas_discover_expander) | YES (initial ref from sas_alloc_device) | YES (sas_discover_expander does an unconditional put, consuming the initial ref) THEN sas_put_device does another put → EXCESS | ❌ EXCESS PUT | sas_discover_expander already dropped the initial reference; the extra sas_put_device causes a refcount underflow |
| ~L965 | return child (success) | YES (initial ref) | sas_discover_expander may have done a get+put (net zero); no extra put | ✅ | caller holds the returned reference; no extra put on this path |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
sas_discover_expander(child) performs an unconditional put (per contract), consuming the initial reference from sas_alloc_device; the error path then calls sas_put_device(child) again, causing an excess put and refcount underflow.
```
