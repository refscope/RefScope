# REAL BUG: drivers/scsi/mpi3mr/mpi3mr_os.c:1499 mpi3mr_devstatuschg_evt_bh()

**Confidence**: HIGH | **Counter**: `$->ref_count.refcount.refs.counter`

## Reasoning

No ownership transfer or deferred cleanup salvages this path; the extra put is reachable and unconditional on that path.

## Full Response

```
```
| Flow # | Path Description | GET Done? | PUTs on Path | Balanced? | Notes |
|--------|------------------|-----------|--------------|-----------|-------|
| 1 | tgtdev = NULL (L1493 goto out) → out label | NO  | N/A (tgtdev NULL) | ✅ | |
| 2 | GET succeeds, delete=0, cleanup=0 (uhide only) | YES | out PUT (L1502) | ✅ | |
| 3 | GET succeeds, delete=1, cleanup=0 (Hidden) | YES | out PUT (L1502) | ✅* | *If mpi3mr_remove_tgtdev_from_host does NOT put; otherwise excess, but not warned. Not needed for verdict. |
| 4 | GET succeeds, delete=1, cleanup=1 (VD_NOT_RESPONDING) | YES | ① mpi3mr_tgtdev_del_from_list → **internal put** (contract), ② **explicit put** at L1499, ③ **out PUT** at L1502 → total **3 puts** | ❌ **EXCESS** | get only 1 reference from `mpi3mr_get_tgtdev_by_handle`. The explicit put at L1499 is superfluous because out will do it. |

**Contractual analysis**:
- `mpi3mr_get_tgtdev_by_handle` returns a pointer with exactly **one** elevated reference (if non‑NULL).  
- `mpi3mr_tgtdev_del_from_list` internally calls `mpi3mr_tgtdev_put` (releasing a separate list reference).  
- The function **always** does `mpi3mr_tgtdev_put(tgtdev)` at the `out` label if `tgtdev` is non‑NULL.  

On the `cleanup` path, the code does **two** puts of the caller’s reference: once explicitly inside the `if (cleanup)` block (line 1499) and again unconditionally at the `out` label. This creates a refcount imbalance: **one get, two puts → refcount excess put**. The warning pinpointed the extra put at line 1499.

No ownership transfer or deferred cleanup salvages this path; the extra put is reachable and unconditional on that path.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
The `cleanup` path in `mpi3mr_devstatuschg_evt_bh` performs both an explicit `mpi3mr_tgtdev_put` at line 1499 and a fall‑through put at the `out` label, resulting in a double free of the reference acquired by `mpi3mr_get_tgtdev_by_handle`.```
```
