# REAL BUG: drivers/nvme/host/pci.c:3844 nvme_probe()

**Confidence**: HIGH | **Counter**: `dev->ctrl.device.kobj.kref.refcount.refs.counter`

## Reasoning

| success path (return 0) | success | YES | YES (1 put, nvme_put_ctrl) | ✅ | single put matches the initial get |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| IS_ERR(dev) | early error | NO (before get) | N/A | ✅ | get hasn’t happened |
| nvme_add_ctrl fails → goto out_put_ctrl | error | YES (unconditional get) | YES (1 put at out_put_ctrl) | ✅ | single put balances the get |
| nvme_dev_map fails → goto out_uninit_ctrl | error | YES (add succeeded) | YES (2 puts: nvme_uninit_ctrl → put + out_put_ctrl→ put) | ❌ | **double put** |
| nvme_pci_alloc_iod_mempool fails → goto out_dev_unmap | error | YES | YES (2 puts, via out_dev_unmap→out_uninit_ctrl→out_put_ctrl) | ❌ | **double put** |
| nvme_pci_enable fails → goto out_release_iod_mempool | error | YES | YES (2 puts) | ❌ | **double put** |
| nvme_alloc_admin_tag_set fails → goto out_disable | error | YES | YES (2 puts) | ❌ | **double put** |
| nvme_change_ctrl_state(CONNECTING) fails → goto out_disable | error | YES | YES (2 puts) | ❌ | **double put** |
| nvme_init_ctrl_finish fails → goto out_disable | error | YES | YES (2 puts) | ❌ | **double put** |
| nvme_setup_host_mem fails → goto out_disable | error | YES | YES (2 puts) | ❌ | **double put** |
| nvme_setup_io_queues fails → goto out_disable | error | YES | YES (2 puts) | ❌ | **double put** |
| nvme_change_ctrl_state(LIVE) fails → goto out_disable | error | YES | YES (2 puts) | ❌ | **double put** |
| success path (return 0) | success | YES | YES (1 put, nvme_put_ctrl) | ✅ | single put matches the initial get |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`nvme_uninit_ctrl()` already calls `nvme_put_ctrl()`, so all error paths that fall through from `out_uninit_ctrl` to `out_put_ctrl` release the reference twice, causing the excess put on the controller’s kref.
```
