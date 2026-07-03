# REAL BUG: net/tipc/crypto.c:1885 tipc_crypto_rcv()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| L1881  | normal exit         | YES (if aead non-NULL) | YES            | ✅          | tipc_crypto_rcv_complete() calls tipc_aead_put() to release the reference                                                             |

## Full Response

```
```
| Line   | Return Type         | GET Done?      | PUT Done?      | Balanced?   | Notes                                                                                                                                 |
|--------|---------------------|----------------|----------------|-------------|----------------------------------------------------------------------------------------------------------------------------------------|
| L1854  | early error (EINPROGRESS/EBUSY) | YES (aead non-NULL) | NO             | ❌ LEAK      | decrypt always acquires aead; no tipc_crypto_rcv_complete/put called                                                                 |
| L1873  | early error (ENOKEY, aead non-NULL) | YES (aead non-NULL) | NO             | ❌ LEAK      | decrypt returned ENOKEY with aead acquired; no tipc_crypto_rcv_complete/put                                                           |
| L1873  | early error (ENOKEY, aead NULL)     | NO             | N/A            | ✅          | pick_tx failed, no decrypt; aead never acquired                                                                                       |
| L1881  | normal exit         | YES (if aead non-NULL) | YES            | ✅          | tipc_crypto_rcv_complete() calls tipc_aead_put() to release the reference                                                             |
```

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`tipc_crypto_rcv()` acquires an aead reference via `tipc_crypto_key_pick_tx()` or `tipc_aead_get()` but leaks it on the `-EINPROGRESS`/`-EBUSY` (L1854) and `-ENOKEY` (when decrypt ran, L1873) early return paths because they skip `tipc_crypto_rcv_complete()`, which is the only place that releases the aead.
```
