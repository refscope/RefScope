# REAL BUG: net/tipc/crypto.c:1995 tipc_crypto_rcv_complete()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| ~L1950 | non‑TX, `msg_validate` fail → `goto free_skb` | NO | YES | ❌ | |

## Full Response

```
| Line | Path Description | GET Done? | PUT Done? | Balanced? | Notes |
|------|------------------|-----------|-----------|-----------|-------|
| ~L1906 | TX block, early err → `goto free_skb` | NO (rx from tx_clone_ctx.rx) | YES (if rx) | ❌ (if rx non‑NULL) | No create; rx may be set |
| ~L1917 | TX block, `!rx` creation fails → `goto free_skb` | NO (rx=NULL) | NO | ✅ | rx NULL after failure |
| ~L1921‑1925 | TX block, `!rx` creation succeeds → `goto rcv`/fall‑through | YES (from `tipc_node_create`) | YES | ✅ | Ref held on node, put at exit |
| ~L1921 | TX block, rx already set (no creation) → `goto rcv`/exit | NO | YES | ❌ | No get, but node put at exit |
| ~L1932 | non‑TX, `err` true → `goto free_skb` | NO | YES | ❌ | `rx = aead->crypto`, no get |
| ~L1947 | non‑TX, `pskb_trim` fail → `goto free_skb` | NO | YES | ❌ | |
| ~L1950 | non‑TX, `msg_validate` fail → `goto free_skb` | NO | YES | ❌ | |
| ~L1961/L1965 | non‑TX, success exit | NO | YES | ❌ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Every non‑TX path (and TX paths where `rx` was already non‑NULL with no `tipc_node_create`) reaches `exit:` with `rx` set but without a matching get, causing an excess `kref_put`.
```
