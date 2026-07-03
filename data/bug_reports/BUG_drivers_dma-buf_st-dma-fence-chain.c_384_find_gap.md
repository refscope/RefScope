# REAL BUG: drivers/dma-buf/st-dma-fence-chain.c:384 find_gap()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| L380 | normal return 0           | YES | NO | ❌ LEAK | loop completes; all iterations leak original reference(s) |

## Full Response

```
| Line | Return Type | GET Done? (fc.tail ref) | PUT Done? (on correct object) | Balanced? | Notes |
|------|-------------|--------------------------|-------------------------------|-----------|-------|
| L347 | return -err   | NO (before any get)      | N/A                           | ✅ | early exit if fence_chains_init fails |
| L356 | goto err (find_seqno error) | YES (get at L351) | NO (put at L353 goes to fence modified by find_seqno, not the original fc.tail) | ❌ LEAK | dma_fence_chain_find_seqno overwrites pointer before dma_fence_put; original reference leaked |
| L361 | goto err (chain mismatch)  | YES | NO | ❌ LEAK | same as above |
| L369 | goto err (2nd find_seqno error) | YES | NO | ❌ LEAK | get1 (L351) leaked, get2 (L364) also lost after find_seqno changes pointer |
| L374 | goto err (2nd mismatch)     | YES | NO | ❌ LEAK | same as above |
| L380 | normal return 0           | YES | NO | ❌ LEAK | loop completes; all iterations leak original reference(s) |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
dma_fence_get(fc.tail) takes a reference, but dma_fence_chain_find_seqno overwrites the `fence` pointer before the matching dma_fence_put, so the put releases the new fence instead of the original, leaving the tail‑fence reference leaked on every loop path.
```
