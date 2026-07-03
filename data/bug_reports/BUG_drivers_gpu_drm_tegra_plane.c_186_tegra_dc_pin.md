# REAL BUG: drivers/gpu/drm/tegra/plane.c:186 tegra_dc_pin()

**Confidence**: HIGH | **Counter**: `$->ref.refcount.refs.counter`

## Reasoning

| L176 (via L160) | error (after unpin loop) | YES | NO | ❌ LEAK | cleanup loop skips the current leaked map |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L150 | error (goto unpin) | NO (map is ERR_PTR) | YES (unpin previous planes) | ✅ | get failed, no ref held |
| L160 | error (goto unpin) | YES (map valid) | NO (current map not unpinned) | ❌ LEAK | map created but not stored; unpin loop misses it |
| L168 | success | YES (all planes) | NO (intentional) | N/A | successfully pinned, refs held for later use |
| L176 (via L160) | error (after unpin loop) | YES | NO | ❌ LEAK | cleanup loop skips the current leaked map |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On the chunks>1 error path (L160), host1x_bo_pin() returns a valid mapping with an extra reference, but the unpin loop only cleans up previous planes; the current mapping is lost without host1x_bo_unpin().
```
