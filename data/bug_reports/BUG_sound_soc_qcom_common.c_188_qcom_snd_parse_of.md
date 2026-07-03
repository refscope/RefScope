# REAL BUG: sound/soc/qcom/common.c:188 qcom_snd_parse_of()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L188 return ret (after err) | error path from err label | depends on path; for L142 case YES | NO | ❌ LEAK | err label puts cpu/codec/platform from of_get_child_by_name, but not the phandle node |

## Full Response

```
| Line | Return Type | GET Done? (platform phandle) | PUT Done? (platform phandle) | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L46 | early return (no get) | N/A | N/A | ✅ | Before any DT node acquisitions |
| L52 | early return (no get) | N/A | N/A | ✅ | |
| L58 | early return (no get) | N/A | N/A | ✅ | |
| L63 | early return (no get) | N/A | N/A | ✅ | |
| L68 | early return (no get) | N/A | N/A | ✅ | |
| L72 | early return (no get) | N/A | N/A | ✅ | |
| L80 | early return (no get) | N/A | N/A | ✅ | dais_link alloc failure |
| L89 goto err_put_np | error before of_get_child_by_name | N/A | N/A | ✅ | dlc alloc failure, no node refs held |
| L98 goto err_put_np | error before of_get_child_by_name | N/A | N/A | ✅ | property read failure |
| L108 goto err | cpu missing, platform not yet accessed | N/A | N/A | ✅ | platform ref from of_get_child_by_name released at err |
| L114 goto err | snd_soc_of_get_dlc failure | N/A | N/A | ✅ | no of_parse_phandle call yet |
| L121 goto err | invalid cpu id | N/A | N/A | ✅ | no of_parse_phandle call yet |
| L130 goto err | of_parse_phandle returned NULL | NO (call failed) | N/A | ✅ | no extra ref taken, platform original ref freed at err |
| **L142 goto err** | codec error after of_parse_phandle success | **YES** (of_parse_phandle at L124 succeeded) | **NO** (err label only puts of_get_child_by_name refs) | ❌ **LEAK** | phandle reference on platform’s sound-dai node not released |
| L180 return 0 (success) | loop complete, success path | YES | NO (intentionally kept for card lifetime) | ✅ (lifetime) | phandle ref stored in link->platforms->of_node, freed later by card removal |
| L188 return ret (after err) | error path from err label | depends on path; for L142 case YES | NO | ❌ LEAK | err label puts cpu/codec/platform from of_get_child_by_name, but not the phandle node |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Error path at L142 (goto err after codec error) leaks the device_node reference obtained by of_parse_phandle at L124; the err label does not release link->platforms->of_node.
```
