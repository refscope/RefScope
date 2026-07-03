# REAL BUG: drivers/misc/ibmasm/module.c:151 ibmasm_init_one()

**Confidence**: HIGH | **Counter**: `$->heartbeat->kref.refcount.refs.counter`

## Reasoning

| L110 (success) | return 0 | YES | NO (held for device lifetime) | ⚠️ FP zone (released in remove) | Balanced across lifecycle, but not locally |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L56 (pci_enable fail) | error return | NO (before get) | N/A | ✅ | |
| L60 (pci_request_reg fail) | goto error_resources | NO (before get) | N/A | ✅ | |
| L68 (kzalloc fail) | goto error_kmalloc | NO (before get) | N/A | ✅ | |
| L77 (event_buffer_init fail) | goto error_eventbuffer | NO (before get) | N/A | ✅ | |
| L82 (heartbeat_init fail) | goto error_heartbeat | **YES** (unconditional GET) | **NO** (label skips exit) | ❌ **LEAK** | error_heartbeat: only event_buffer_exit, no heartbeat_exit |
| L91 (pci_ioremap fail) | goto error_ioremap | YES (heartbeat_init succeeded) | YES (via error_ioremap → exit) | ✅ | |
| L95 (request_irq fail) | goto error_request_irq | YES | YES (via error_request_irq → error_ioremap → exit) | ✅ | |
| L99 (init_remote fail) | goto error_init_remote | YES | YES (via chain) | ✅ | |
| L104/106 (send_message fail) | goto error_send_message | YES | YES (via chain) | ✅ | |
| L110 (success) | return 0 | YES | NO (held for device lifetime) | ⚠️ FP zone (released in remove) | Balanced across lifecycle, but not locally |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`ibmasm_heartbeat_init` is an unconditional GET (always sets refcount 1) per contract; its failure path (`goto error_heartbeat`) skips `ibmasm_heartbeat_exit`, causing a kref leak on that error return.
```
