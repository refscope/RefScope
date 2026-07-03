# REAL BUG: net/batman-adv/routing.c:274 batadv_recv_my_icmp_packet()

**Confidence**: MEDIUM | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

tion internally drops the caller’s reference to `orig_node` (analogous to how it “consumed” `skb`, after which `skb` is set to `NULL`), then the subsequent unconditional `batadv_orig_node_put(orig_node)` is an excess decrement. The reported “refcount excess put” strongly suggests this is the case.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L230 (goto out) | early error / primary_if NULL | NO (get failed) | batadv_hardif_put(NULL) safe → no real put | ✅ | conditional get returned NULL, no ref held |
| L235 (goto out) | early error / orig_node NULL | YES (primary_if) | YES (primary_if put via hardif_put) | ✅ | orig_node not obtained, put on NULL is safe |
| L239 (goto out) | skb_cow failure | YES (both gets) | YES (both puts) | ✅ *if orig_node ref not consumed earlier* | balanced if send never called |
| L254 (break → reaches `out:` after `batadv_send_skb_to_orig`) | normal ECHO_REPLY path | YES (both gets) | YES (both puts) | ❌ **POTENTIAL EXCESS** | `batadv_send_skb_to_orig()` may consume the orig_node reference (common pattern), leaving `orig_node` still non‑NULL → `batadv_orig_node_put()` at L270 becomes an extra put, matching “refcount excess put” warning |
| L257 (goto out) | early error in TP case | NO (no get calls) | puts on NULL safe | ✅ | |
| L263 (goto out) | normal TP path | NO | puts on NULL safe | ✅ | |
| L266 (goto out) | default / unknown type | NO | puts on NULL safe | ✅ | |

`batadv_send_skb_to_orig()` is not shown in the provided context. If this function internally drops the caller’s reference to `orig_node` (analogous to how it “consumed” `skb`, after which `skb` is set to `NULL`), then the subsequent unconditional `batadv_orig_node_put(orig_node)` is an excess decrement. The reported “refcount excess put” strongly suggests this is the case.

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
`batadv_recv_my_icmp_packet()` does not set `orig_node = NULL` after `batadv_send_skb_to_orig()`, leaving an extra `batadv_orig_node_put()` for the ECHO_REPLY path, which matches the “excess put” warning.
```
