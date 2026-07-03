# REAL BUG: sound/soc/loongson/loongson_card.c:164 loongson_card_parse_of()

**Confidence**: MEDIUM | **Counter**: `codec->kobj.kref.refcount.refs.counter`

## Reasoning

| L162 (err) | return ret (indirect) | cpu: YES, codec: YES | cpu: YES, codec: YES | ❌ | err label (reachable from L144/L151) puts both. Same double‑put risk as above. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L131 | return -EINVAL | cpu: NO (get failed, NULL) | cpu: N/A; codec: N/A | ✅ | cpu was NULL, no reference to put |
| L137 | return -EINVAL | cpu: YES (non‑NULL from L128), codec: NO (NULL from L133) | cpu: YES (of_node_put at L136), codec: N/A | ✅ | correct path: put cpu, return error |
| L144 | goto err | cpu: YES, codec: YES | cpu: YES (L161), codec: YES (L162) | ❌ | snd_soc_of_get_dlc for cpu failed; err label puts both. If snd_soc_of_get_dlc does NOT take a reference on the passed node, this put is valid for the original ref, but the card’s cleanup later will put the stored of_node again → overall excess put. |
| L151 | goto err | cpu: YES, codec: YES | cpu: YES (L161), codec: YES (L162) | ❌ | snd_soc_of_get_dlc for codec failed; same double‑put issue as L144. |
| L158 | return 0 | cpu: YES, codec: YES | cpu: YES (L155), codec: YES (L156) | ❌ | Successful path puts both. If snd_soc_of_get_dlc does not own a reference, later ASoC core cleanup will put the stored of_node again → excess put on codec (and cpu). |
| L162 (err) | return ret (indirect) | cpu: YES, codec: YES | cpu: YES, codec: YES | ❌ | err label (reachable from L144/L151) puts both. Same double‑put risk as above. |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
snd_soc_of_get_dlc likely does NOT increment the node refcount (or the card cleanup unconditionally puts stored of_nodes), so the explicit of_node_put(codec) here will lead to a later double-put, matching the observed refcount excess put.
```
