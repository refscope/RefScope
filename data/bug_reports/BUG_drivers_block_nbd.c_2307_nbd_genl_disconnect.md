# REAL BUG: drivers/block/nbd.c:2307 nbd_genl_disconnect()

**Confidence**: HIGH | **Counter**: `nbd->config_refs.refs.counter`

## Reasoning

YES | YES (nbd_put at put_nbd, plus internal nbd_puts via nbd_config_put calls in nbd_disconnect_and_put) | YES (nbd_config_put inside nbd_disconnect_and_put twice + explicit nbd_config_put once = 3 puts) | ❌ EXCESS PUT on config_refs | 1 config_refs get, 3 config_refs puts → refcount underflow |

## Full Response

```
| Line | Return Type | GET nbd->refs? | GET config_refs? | PUT nbd->refs? | PUT config_refs? | Balanced? | Notes |
|------|-------------|-----------------|-------------------|----------------|-------------------|-----------|-------|
| L2279 | error (-EPERM) | NO | NO | N/A | N/A | ✅ | before any get |
| L2284 | error (-EINVAL) | NO | NO | N/A | N/A | ✅ | before any get |
| L2292 | error (-EINVAL) | NO | NO | N/A | N/A | ✅ | idr_find returns NULL |
| L2297 | error (-EINVAL) | NO (get failed) | NO | N/A | N/A | ✅ | refcount_inc_not_zero(&nbd->refs) failed, no ref held |
| L2302 | goto put_nbd (return 0) | YES | NO (get failed) | YES (nbd_put) | NO | ✅ | config_refs get failed, only nbd->refs acquired then put |
| L2306 | fallthrough (return 0) | YES | YES | YES (nbd_put at put_nbd, plus internal nbd_puts via nbd_config_put calls in nbd_disconnect_and_put) | YES (nbd_config_put inside nbd_disconnect_and_put twice + explicit nbd_config_put once = 3 puts) | ❌ EXCESS PUT on config_refs | 1 config_refs get, 3 config_refs puts → refcount underflow |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
After a successful `refcount_inc_not_zero(&nbd->config_refs)`, the code calls `nbd_disconnect_and_put()` (which, per contract, calls `nbd_config_put` twice) followed by an explicit `nbd_config_put()`, resulting in three config_refs puts for one config_refs get.
```
