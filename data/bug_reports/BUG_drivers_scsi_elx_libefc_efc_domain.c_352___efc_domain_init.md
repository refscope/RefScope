# REAL BUG: drivers/scsi/elx/libefc/efc_domain.c:352 __efc_domain_init()

**Confidence**: LOW | **Counter**: `nport->ref.refcount.refs.counter`

## Reasoning

of that state handler, we cannot determine whether it releases the nport. Therefore, the excess‑put warning hinges on an unknown callee.

## Full Response

```
## Path Table for `__efc_domain_init` (Explicit Get/Put of nport)

| Line (approx) | Return Type / Exit           | GET Done? (efc_nport_alloc) | PUT Done? (efc_nport_free) | Balanced? | Notes                                                                                                                                                  |
|---------------|------------------------------|-----------------------------|----------------------------|-----------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| ~264          | efc_nport_alloc fails → break | NO (IS_ERR/NULL guard)     | N/A                        | ✅        | nport is NULL; no ref held.                                                                                                                             |
| ~290          | efc_cmd_nport_alloc fails → efc_nport_free → break | YES                        | YES                        | ✅        | Explicit put after allocation failure; this appears balanced on its own.                                                                                |
| ~305 (non-loop branch) | efc_cmd_domain_alloc fails → break | YES                        | NO                         | ❌ LEAK  | Path after efc_cmd_nport_alloc success; nport not freed → refcount leak.                                                                               |
| ~310 (non-loop branch) | efc_cmd_domain_alloc succeeds → transition → break | YES                        | NO (ownership xfer?)       | ?         | nport handed to state machine; likely ownership transferred, cleanup done later.                                                                        |
| ~340 (loop branch)   | efc_cmd_domain_alloc fails → break | YES                        | NO                         | ❌ LEAK  | After loop setup; nport still allocated, never freed → leak.                                                                                           |
| ~345 (loop branch)   | efc_cmd_domain_alloc succeeds → transition → break | YES                        | NO (ownership xfer?)       | ?         | Handoff to state machine.                                                                                                                               |

*Note: Line numbers are approximate (based on snippet + 10‑line header). The snippet shown starts at line 230, so the `efc_nport_free` call is around 264, not 352. The warning line (352) is likely elsewhere in the file, possibly a different call site or macro‑generated code.*

## Pre‑Verdict Checklist

1. **“Held for device lifetime”?** – Not explicitly claimed for nport. Success paths hand off nport; error paths after the handoff (domain alloc failures) leak the nport. Those leaks are not “excess put”, they are missing puts. The warning is about an *excess* put, not a leak.
2. **“Ownership transferred”?** – The handoff to `__efc_nport_a
```
