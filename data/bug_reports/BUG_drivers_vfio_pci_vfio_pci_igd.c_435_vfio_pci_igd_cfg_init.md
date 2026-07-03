# REAL BUG: drivers/vfio/pci/vfio_pci_igd.c:435 vfio_pci_igd_cfg_init()

**Confidence**: HIGH | **Counter**: `$->dev.kobj.kref.refcount.refs.counter`

## Reasoning

4. **goto out between GET and PUT?** – Not applicable; no goto.

## Full Response

```
| Line | Return Type | GET Done? (host) | PUT Done? (host) | GET Done? (lpc) | PUT Done? (lpc) | Balanced? | Notes |
|------|-------------|------------------|------------------|-----------------|-----------------|-----------|-------|
| L391 | error       | NO (host_bridge NULL) | N/A | N/A | N/A | ✅ | pci_get… returned NULL, no ref taken |
| L395 | error       | YES | YES (pci_dev_put) | N/A | N/A | ✅ | vendor/class mismatch, host ref released |
| L402 | error       | YES | YES (pci_dev_put) | N/A | N/A | ✅ | host region registration failed, ref released |
| L407 | error       | YES | **NO** | NO (lpc_bridge NULL) | N/A | ❌ **LEAK** | lpc_bridge not found, host ref leaked |
| L411 | error       | YES | **NO** | YES | YES | ❌ **LEAK** | lpc vendor/class mismatch, host ref leaked |
| L418 | error       | YES | **NO** | YES | YES | ❌ **LEAK** | lpc region registration fails, host ref leaked |
| L420 | success     | YES (transferred) | NO (held by region) | YES (transferred) | NO (held by region) | ✅ | ownership transferred to registered regions |

**Pre-Verdict Checklist**

1. **"Held for device lifetime"?** – The host_bridge reference is transferred to the region on success (path 7). However, error paths 4–6 occur BEFORE the device is fully initialized; the region is already registered but the overall init fails, so the reference will never be released. → **YES, leak on error paths.**

2. **"Ownership transferred"?** – On path 7, ownership is transferred to the region data. But on error paths 4–6, the region was registered earlier but no cleanup is performed and the reference is not released. → **Error paths leak.**

3. **Unconditional GET?** – `pci_get_domain_bus_and_slot` is conditional (NULL if not found). After the host_bridge pointer is not NULL, GET=YES on all subsequent paths.

4. **goto out between GET and PUT?** – Not applicable; no goto.

**VERDICT: REAL_BUG**  
**CONFIDENCE: HIGH**  

Host bridge’s `pci_dev_get` reference is leaked on every error path after successful host region registration: when `lpc_bridge` is not found (L407), has mismatched vendor/class (L411), or when its region registration fails (L418). The missing `pci_dev_put(host_bridge)` on these paths leads to a permanent reference leak.
```
