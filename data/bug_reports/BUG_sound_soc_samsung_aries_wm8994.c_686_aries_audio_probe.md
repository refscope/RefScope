# REAL BUG: sound/soc/samsung/aries_wm8994.c:686 aries_audio_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L681 (fallthrough) | success | cpu: YES; codec: YES   | YES (both at out)      | ✅ | balanced; CRITICAL: `aries_dai[0].platforms->of_node = aries_dai[0].cpus->of_node` without `of_node_get`, causing double put later. |

## Full Response

```
| Line | Return Type | GET Done? (cpu/codec) | PUT Done? (cpu/codec) | Balanced? | Notes |
|------|-------------|------------------------|------------------------|-----------|-------|
| L550 | error       | NO (before any get)    | N/A                    | ✅         | |
| L556 | error       | NO                     | N/A                    | ✅         | |
| L570 | error       | NO                     | N/A                    | ✅         | |
| L576 | error       | NO                     | N/A                    | ✅         | |
| L583 | error       | NO                     | N/A                    | ✅         | |
| L590 | error       | NO (cpu/codec not gotten) | N/A (extcon put earlier) | ✅ | extcon_np balanced earlier |
| L595 | error       | NO                     | N/A                    | ✅         | |
| L600 | error       | NO                     | N/A                    | ✅         | |
| L603 | error       | NO                     | N/A                    | ✅         | |
| L609 | error       | NO                     | N/A                    | ✅         | |
| L616 | error       | NO                     | N/A                    | ✅         | |
| L628 | error       | NO                     | N/A                    | ✅         | |
| L636 | error       | cpu: GET called → NULL, no ref | N/A          | ✅ | cpu NULL, no put needed |
| L641 | goto out    | cpu: YES; codec: GET → NULL, no ref | cpu: YES (out); codec: NULL (no-op) | ✅ | cpu balanced |
| L649 | goto out    | cpu: YES; codec: YES   | YES (both at out)      | ✅ | cpu/codec balanced; phandle nodes from loop leaked |
| L658 | goto out    | cpu: YES; codec: YES   | YES (both at out)      | ✅ | balanced; cpus->of_node leaked |
| L668 | goto out    | cpu: YES; codec: YES   | YES (both at out)      | ✅ | balanced; cpus->of_node leaked |
| L675 | goto out    | cpu: YES; codec: YES   | YES (both at out)      | ✅ | balanced |
| L681 (fallthrough) | success | cpu: YES; codec: YES   | YES (both at out)      | ✅ | balanced; CRITICAL: `aries_dai[0].platforms->of_node = aries_dai[0].cpus->of_node` without `of_node_get`, causing double put later. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`aries_dai[0].platforms->of_node` is assigned the same pointer as `cpus->of_node` (from `of_parse_phandle`) without incrementing the refcount, leading to a double `of_node_put` when the sound card releases both pointers — an excess put (refcount underflow).
```
