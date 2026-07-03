# REAL BUG: drivers/clk/sunxi-ng/ccu_common.c:196 sunxi_ccu_probe()

**Confidence**: HIGH | **Counter**: `node->kobj.kref.refcount.refs.counter`

## Reasoning

| L184 (return 0) | success | YES | NO (deferred removal) | ✅ (ownership transferred) | provider kept for device lifetime; removed elsewhere |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L147 (goto err_clk_unreg) | error from clock registration loop → returns at L196 | NO (before of_clk_add_hw_provider) | N/A | ✅ | no get executed yet |
| L169 (goto err_clk_unreg) after `of_clk_add_hw_provider()` failure | error, ret ≠ 0 → returns at L196 | **YES** (unconditional GET per contract) | **NO** (err_clk_unreg has no `of_clk_del_provider`) | ❌ **LEAK** | ref acquired but no put on error path |
| L182 (goto err_del_provider) after `reset_controller_register()` failure | error → `of_clk_del_provider(node)` → falls through to err_clk_unreg → returns at L196 | YES | YES (`of_clk_del_provider` at L187) | ✅ | release done |
| L184 (return 0) | success | YES | NO (deferred removal) | ✅ (ownership transferred) | provider kept for device lifetime; removed elsewhere |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`of_clk_add_hw_provider` is contractually unconditional – it always increments the ref on `node`. When it fails (L168-169), the code jumps to `err_clk_unreg` and eventually returns at L196 without calling `of_clk_del_provider`, leaking the reference.
```
