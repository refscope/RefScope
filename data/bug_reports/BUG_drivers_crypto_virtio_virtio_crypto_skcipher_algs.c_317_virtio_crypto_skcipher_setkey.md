# REAL BUG: drivers/crypto/virtio/virtio_crypto_skcipher_algs.c:317 virtio_crypto_skcipher_setkey()

**Confidence**: MEDIUM | **Counter**: `$->ref_count.counter`

## Reasoning

| L317 | success (return 0) | YES (first call); NO (rekey) | NO | ✅ | If `init_sessions` put on success, this would be excess put at this line. |

## Full Response

```
[NEED_SOURCE] virtio_crypto_alg_skcipher_init_sessions
[NEED_SOURCE] virtcrypto_get_dev_node
[NEED_SOURCE] virtcrypto_dev_put

## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L289 | error (validate) | NO | N/A | ✅ | |
| L299 | error (no vcrypto) | NO (get returned NULL) | N/A | ✅ | |
| L314 | error (init fail) | YES (if first call); NO (rekey) | YES (explicit) | ⚠️ potentially unbalanced | If `init_sessions` already put on error, this is a double put. |
| L317 | success (return 0) | YES (first call); NO (rekey) | NO | ✅ | If `init_sessions` put on success, this would be excess put at this line. |

## VERDICT: REAL_BUG
CONFIDENCE: MEDIUM

The only explicit `virtcrypto_dev_put()` is on the error path (L311 in snippet, L314 in table). The warning reports “excess put” at line 317 (the `return 0;` line), implying that the refcount may have been over-decremented. If `virtio_crypto_alg_skcipher_init_sessions()` internally calls `virtcrypto_dev_put()` on failure, then the error-path put in `setkey()` is a double put. The warning’s location on the success return may indicate that the refcount inconsistency manifests there (e.g., stale state after a previous excess put). Without the callee source, I cannot rule out a bug in the error handling. Requesting source for the key callees to confirm.
```
