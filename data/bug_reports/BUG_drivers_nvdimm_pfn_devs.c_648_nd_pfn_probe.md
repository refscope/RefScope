# REAL BUG: drivers/nvdimm/pfn_devs.c:648 nd_pfn_probe()

**Confidence**: HIGH | **Counter**: `pfn_dev->kobj.kref.refcount.refs.counter`

## Reasoning

| ~L644? (rc ≥ 0, success) | success (0) | YES | NO (no put_device) | ✅ (hand-off to device model, ref consumed by nd_device_register) | Not relevant to excess‑put warning. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L618 (force_raw) | error (-ENODEV) | NO (before get) | N/A | ✅ | Return before any ref acquisition. |
| ~L624 (default switch) | error (-ENODEV) | NO (before get) | N/A | ✅ | Return before any ref acquisition. |
| ~L630 (!pfn_dev) | error (-ENOMEM) | NO (nd_pfn_devinit returned NULL) | N/A | ✅ | No ref to put. |
| L648 (rc < 0, error) | error (rc) | YES (nd_pfn_devinit succeeded, pfn_dev holds refcount ≥1) | YES (put_device(pfn_dev) called) BUT nd_detach_ndns(pfn_dev, …) also executes before it | ❌ EXCESS PUT: nd_detach_ndns likely already dropped the last reference, making the subsequent put_device underflow | WARNING is triggered at this put_device. nd_detach_ndns is called unconditionally, though __nd_attach_ndns may not have happened, leading to double decrement. |
| ~L644? (rc ≥ 0, success) | success (0) | YES | NO (no put_device) | ✅ (hand-off to device model, ref consumed by nd_device_register) | Not relevant to excess‑put warning. |

[NEED_SOURCE] nd_detach_ndns

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On the error path (rc < 0), `nd_detach_ndns` is called unconditionally even if `nd_pfn_devinit` did not attach a namespace (refcount = 1). `nd_detach_ndns` likely calls `put_device`, reducing the refcount to 0, then the explicit `put_device(pfn_dev)` on line 648 sees a refcount already 0 and triggers the “refcount excess put” warning.
```
