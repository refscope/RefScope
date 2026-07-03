# REAL BUG: drivers/bluetooth/btmrvl_main.c:705 btmrvl_register_hdev()

**Confidence**: HIGH | **Counter**: `$->dev.kobj.kref.refcount.refs.counter`

## Reasoning

t L696 drops to 0 (device freed). Then fallthrough to `err_hdev` calls `btmrvl_free_adapter(priv)` which may access `priv->btmrvl_dev.hcidev` (now dangling, set at L670) and call another put → **EXCESS PUT** (matches the warning). Either way—leak or double-put—the fallthrough is broken.

## Full Response

```
## Path Table

```
| Line  | Return Type         | GET Done?                         | PUT Done?                          | Balanced? | Notes                                              |
|-------|---------------------|-----------------------------------|------------------------------------|-----------|----------------------------------------------------|
| L667  | goto err_hdev       | NO (hdev=NULL, alloc failed)      | N/A                                | ✅        | No ref held; hci_free_dev never called             |
| L686  | goto err_hci_reg_dev| YES (alloc, ref=1) + YES (register_dev: unconditional GET per contract, ref→2) | YES: hci_free_dev at L696 drops ref 2→1. Then falls through to err_hdev—NO further put | ❌ LEAK   | 1 ref remains; hdev leaked                         |
| L693  | return 0 (success)  | YES (alloc, ref=1) + YES (register_dev unconditional GET, ref→2) | NO                                 | ✅        | Both refs held for device lifetime; released on teardown |

⚠️ **Additional excess-put scenario on L686 path**: If `hci_register_dev` on failure does NOT retain its internal get (contract says unconditional but the function may release internally on error), then refcount=1 after alloc only. `hci_free_dev` at L696 drops to 0 (device freed). Then fallthrough to `err_hdev` calls `btmrvl_free_adapter(priv)` which may access `priv->btmrvl_dev.hcidev` (now dangling, set at L670) and call another put → **EXCESS PUT** (matches the warning). Either way—leak or double-put—the fallthrough is broken.
```

## PRE-VERDICT CHECKLIST

1. **"Held for device lifetime"?** → YES, but only covers the SUCCESS return (L693). The ERROR path (L686) returns without the device being bound → remove() never fires → MUST release. The code attempts this with `hci_free_dev` at L696, but then falls through to `err_hdev` which calls `btmrvl_free_adapter(priv)`—creating either a leak (if register_dev's unconditional GET is held) or a double-put (if register_dev released internally).

2. **"Ownership transferred"?** → NO. The hdev is stored in `priv->btmrvl_dev.hcidev` at L670, but the error path explicitly frees it at L696, then falls through to adapter cleanup that may try to free it again. No documented cleanup exists that covers this fallthrough.

3. **Unconditional GET?** → YES, per contract `hci_register_dev` unconditionally calls `hci_dev_hold`. Every return after this call MUST put. The error path puts ONCE via `hci_free_dev`, but then falls through with no further put → LEAK of one ref. OR if `hci_register_dev` internally cleans up on failure, the single `hci_free_dev` frees the device, then fallthrough leads to excess put.

4. **goto between GET and PUT?** → `goto err_hci_register_dev` at L686 reaches `hci_free_dev(hdev)` at L696. After that, execution falls through to `err_hdev` (L698) which only does `kthread_stop`, `btmrvl_free_adapter`, `kfree(priv)`, `return -ENOMEM`. No second `hci_free_dev` is present in `err_hdev`. If `btmrvl_free_adapter` i
```
