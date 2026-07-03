# REAL BUG: drivers/scsi/mpt3sas/mpt3sas_scsih.c:12052 _mpt3sas_fw_work()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

del_from_list (put1) + fw_event_work_put (put2) | Balanced only if list ref present. The warning points here, indicating underflow, i.e., the final put decremented a refcount already at zero. | The unconditional del_from_list at function entry is the root cause when the event is not on the list. |

## Full Response

```
[NEED_SOURCE] _scsih_fw_event_del_from_list

| Line   | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|--------|-------------|-----------|-----------|-----------|-------|
| L11947 (early return: remove_host / pci_error_recovery) | early return | YES (work reference) | YES: _scsih_fw_event_del_from_list (put1) + fw_event_work_put (put2) | Conditional: balanced only if fw_event was on list (2 refs → 2 puts). If not on list, list ref missing → put1 extra → put2 underflows on final drop. | The function unconditionally calls del_from_list, which drops a list reference. If the event is not on the list, that put is extra and can lead to the refcount hitting zero prematurely. The subsequent final put (at out) would then be an excess put. |
| L11976 (MPI2_EVENT_SAS_TOPOLOGY_CHANGE_LIST requeue) | early return after requeue | YES (work ref) + GET from _scsih_fw_event_requeue (+1) | PUT: _scsih_fw_event_del_from_list (put1) only | NO (missing put) | The requeue adds a reference but the function never drops the work item’s reference (no final fw_event_work_put). This is a leak (not the cause of the current warning, but a separate bug). |
| L11994 (MPI2_EVENT_PCIE_TOPOLOGY_CHANGE_LIST requeue) | early return after requeue | YES + GET from _scsih_fw_event_requeue | PUT: only del_from_list | NO (missing put) | Same leak as above. |
| L12052 (out label) | normal return | YES (work ref) | PUT: del_from_list (put1) + fw_event_work_put (put2) | Balanced only if list ref present. The warning points here, indicating underflow, i.e., the final put decremented a refcount already at zero. | The unconditional del_from_list at function entry is the root cause when the event is not on the list. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
```
