# REAL BUG: drivers/pci/controller/dwc/pcie-eswin.c:261 eswin_pcie_host_init()

**Confidence**: MEDIUM | **Counter**: `$->perst->deassert_count.counter`

## Reasoning

d**. If it performs its own `reset_control_assert` before returning (common for a “reset sequence” that de‑asserts, waits, then asserts), the `err_phy_init` label illegally calls another assert, causing `refcount excess put` on `deassert_count.counter`.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? (perst deassert) | PUT Done? (perst assert) | Balanced? | Notes |
|------|-------------|----------------------------|--------------------------|-----------|-------|
| L191 | error (ret) | NO (before loop)           | N/A                      | ✅ | clk prepare failed; no perst touched |
| L200 | goto err_deassert | NO (bulk deassert failed; per-loop not reached) | NO (no perst assert) | ✅ | No perst deasserted |
| L212 | goto err_perst | **Uncertain** – some ports may have had `eswin_pcie_perst_reset` succeed (deassert likely) | NO (err_perst does ***not*** assert perst) | ⚠️ Leak? | If deassert happened, assert missing; but warning is “excess put”, not leak |
| L226 | goto err_phy_init | **Yes** – loop completed successfully; perst was deasserted by `eswin_pcie_perst_reset` for all ports | **Yes** – err_phy_init calls `reset_control_assert(port->perst)` for all ports | ❌ Excess assert if the callee already asserted | After err_phy_init, perst already asserted? If callee asserts internally, this is an extra assert → excess put |
| L238 | return 0  (success) | **Yes** (all ports deasserted) | NO (perst left deasserted for operation) | ✅ (intentional) | Perst stays deasserted for device lifetime; no put needed here |
| L241‑244 | fall‑through to err_perst after err_phy_init | (same as L226) | **Yes** (already assured by err_phy_init) | (covered above) | err_perst does bulk assert only, not per‑port |

- The warning location (line 261) is outside the provided function; likely the excess assert happens inside the `err_phy_init` path at line 241‑242.
- The `eswin_pcie_perst_reset` function is **not provided**. If it performs its own `reset_control_assert` before returning (common for a “reset sequence” that de‑asserts, waits, then asserts), the `err_phy_init` label illegally calls another assert, causing `refcount excess put` on `deassert_count.counter`.

**[NEED_SOURCE] eswin_pcie_perst_reset**

## VERDICT: REAL_BUG

**CONFIDENCE: MEDIUM**

The `err_phy_init` error path unconditionally asserts `port->perst` for every port. If `eswin_pcie_perst_reset` already asserted the PERST# signal, this extra assert triggers an “excess put” on the reset control’s deassert_count, exactly matching the warning. Without the callee source we cannot be *absolutely* certain, but the pattern strongly indicates a double‑assert bug.
```
