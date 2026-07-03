# REAL BUG: drivers/pci/controller/pcie-brcmstb.c:839 brcm_pcie_bridge_sw_init_set_generic()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

All four questions confirm the leak.

## Full Response

```
Now I'll analyze this warning step by step.

## 🔴 Contract-Driven Reasoning

- **GET** `reset_control_deassert()` increments `deassert_count`.
- **PUT** `reset_control_assert()` decrements `deassert_count`.

The warning at line 839 is about the `deassert_count.counter`. I need to check whether every path that executes the GET also executes a PUT.

---

## Main Function Source Analysis

`brcm_pcie_bridge_sw_init_set_generic()` (lines 816–839):

```c
static int brcm_pcie_bridge_sw_init_set_generic(struct brcm_pcie *pcie, u32 val)
{
	u32 tmp, mask = RGR1_SW_INIT_1_INIT_GENERIC_MASK;
	u32 shift = RGR1_SW_INIT_1_INIT_GENERIC_SHIFT;
	int ret = 0;

	if (pcie->bridge_reset) {               // L820
		if (val)                             // L821
			ret = reset_control_assert(pcie->bridge_reset);      // PUT
		else
			ret = reset_control_deassert(pcie->bridge_reset);    // GET

		if (ret)                             // L826
			dev_err(pcie->dev, "failed to %s 'bridge' reset, err=%d\n",
				val ? "assert" : "deassert", ret);

		return ret;                          // L829
	}

	tmp = readl(pcie->base + PCIE_RGR1_SW_INIT_1(pcie));
	tmp = (tmp & ~mask) | ((val << shift) & mask);
	writel(tmp, pcie->base + PCIE_RGR1_SW_INIT_1(pcie));

	return ret;                              // L836
}
```

---

## 📊 Path Table (Every Return Path)
```
| Line | Return Type                              | GET Done?                                  | PUT Done? | Balanced? | Notes |
|------|------------------------------------------|--------------------------------------------|-----------|-----------|-------|
| L836 | success (pcie->bridge_reset == NULL)    | NO                                         | N/A       | ✅        | No reset operations at all |
| L829 | error/success (val != 0, asserts)       | NO                                         | YES (assert) | ✅     | Assert is a PUT, not a GET |
| L829 | error (val == 0, deassert fails, ret != 0) | NO (GET only on success, conditional)    | NO        | ✅        | Deassert error → no reference held |
| L829 | success (val == 0, deassert succeeds, ret == 0) | **YES** (deassert increments)       | **NO**    | **❌ LEAK** | Returns without reset_control_assert |
```

**Explanation:**
- When `pcie->bridge_reset` is non‑NULL and `val` is 0, we call `reset_control_deassert()` (GET). If it succeeds, `deassert_count` is incremented, but the function immediately returns without ever calling `reset_control_assert()`.  
- The other paths either never call GET, call only PUT, or fail the GET (so no reference is held).  
- Therefore, the highlighted path leaks the count.

---

## 🔎 Pre‑Verdict Checklist

1. **"Held for device lifetime"?**  
   Not applicable here – this is a single setter function with no continuation that would assert later. The function returns immediately after the deassert; no "remove" or "lifetime" pattern exists within this scope.

2. **"Ownership transferred"?**  
   No ownership transfer happens – there is no list/hash/c
```
