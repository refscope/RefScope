# REAL BUG: drivers/scsi/mpi3mr/mpi3mr_os.c:2012 mpi3mr_pcietopochg_evt_bh()

**Confidence**: HIGH | **Counter**: `$->ref_count.refcount.refs.counter`

## Reasoning

| all other `reason_code` (default) | falls through to post-switch | YES | YES (post-switch `mpi3mr_tgtdev_put(tgtdev)`) | ✅ | one get, one put |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| `fwevt->discard` return | early return from loop | NO (no get in this iteration) | N/A  | ✅ | ref not acquired |
| `if (!handle) continue` | continue | NO | N/A  | ✅ | |
| `if (!tgtdev) continue` | continue | NO (get failed) | N/A  | ✅ | conditional `mpi3mr_get_tgtdev_by_handle` returned NULL |
| `reason_code == MPI3_EVENT_PCIE_TOPO_PS_NOT_RESPONDING` (inside case) | falls through to post-switch | YES | YES (2 puts: `mpi3mr_tgtdev_del_from_list` + explicit `mpi3mr_tgtdev_put`) | ❌ EXCESS PUT | `tgtdev` not set to NULL → post-switch `mpi3mr_tgtdev_put(tgtdev)` adds third put |
| all other `reason_code` (default) | falls through to post-switch | YES | YES (post-switch `mpi3mr_tgtdev_put(tgtdev)`) | ✅ | one get, one put |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
When `reason_code` is `MPI3_EVENT_PCIE_TOPO_PS_NOT_RESPONDING`, the code already releases the reference from `mpi3mr_get_tgtdev_by_handle` (via `mpi3mr_tgtdev_del_from_list` + an explicit `mpi3mr_tgtdev_put`), but `tgtdev` remains non-NULL and the unconditional `if (tgtdev) mpi3mr_tgtdev_put(tgtdev)` after the switch also executes, causing a third put – an excess put that frees the object prematurely.
```
```
