# REAL BUG: drivers/i2c/muxes/i2c-demux-pinctrl.c:288 i2c_demux_pinctrl_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L270 | return 0 (success) | YES for all i | NO (held for device lifetime) | ✅ | nodes kept; removal path (not shown) expected to `of_node_put` |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L216 | return -EINVAL | NO (before loop) | N/A | ✅ | num_chan check, no node obtained |
| L223 | return -ENOMEM | NO (before loop) | N/A | ✅ | memory allocation failure, no nodes yet |
| L228 | return err (of_property_read_string) | NO (before loop) | N/A | ✅ | property read error, no nodes yet |
| L236 | goto err_rollback (of_parse_phandle failed) | NO for current i (adap_np NULL) | YES for j < i (previous nodes) | ✅ | NULL return → no ref held; rollback correctly puts prior nodes |
| **L244** | **goto err_rollback** (props name/value alloc failed) | **YES** for current i (adap_np non-NULL) | **NO** for current i (loop only releases j < i) | **❌ LEAK** | `of_parse_phandle` succeeded, but rollback does not put the i‑th node |
| L260 | goto err_rollback (activate master failed) | YES for all i (0..num_chan-1) | YES (j < num_chan releases all) | ✅ | all nodes acquired and released |
| L264 | goto err_rollback_activation | YES for all i | YES (rollback after deactivation) | ✅ | same as above after deactivate master |
| L268 | goto err_rollback_available | YES for all i | YES (rollback) | ✅ | full cleanup after file remove + deactivate |
| L270 | return 0 (success) | YES for all i | NO (held for device lifetime) | ✅ | nodes kept; removal path (not shown) expected to `of_node_put` |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
At `drivers/i2c/muxes/i2c-demux-pinctrl.c:244`, when `props[i].name` or `props[i].value` allocation fails after a successful `of_parse_phandle` for channel `i`, the `goto err_rollback` only releases nodes for indices `j < i`, leaving the `i`-th node’s reference leaked. This makes the kref refcounter inconsistent with the acquisition paths.
```
