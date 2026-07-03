# REAL BUG: drivers/dma-buf/st-dma-fence-chain.c:161 fence_chains_init()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| L147 | success | YES (all chains have enable_sw_signaling) | N/A (caller later releases) | ✅ | success path leaves ownership to caller who will disable signaling and put |

## Full Response

```
| Line | Return Type | GET Done? (enable_sw_signaling) | PUT Done? (enable_sw_signaling) | Balanced? | Notes |
|------|-------------|--------------------------------|----------------------------------|-----------|-------|
| L121 | error (early) | NO (no chains created) | N/A | ✅ | fc->chains alloc failed, no fence objects exist |
| L125→err_chains→L157 | error | NO (no chains created) | N/A | ✅ | fc->fences alloc failed, no chains exist |
| L132-133 (goto unwind, mock_fence fail at i) | error | YES if i>0 (chains[0..i-1] have enable_sw_signaling calls) | NO | ❌ LEAK (if i>0) | unwind puts fences/chains once, but enable_sw_signaling’s extra reference is never dropped |
| L137-139 (goto unwind, mock_chain fail at i) | error | YES for chains[0..i-1] (enable_sw_signaling called) | NO | ❌ LEAK | same as above; enable reference on earlier chains leaked |
| L147 | success | YES (all chains have enable_sw_signaling) | N/A (caller later releases) | ✅ | success path leaves ownership to caller who will disable signaling and put |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`dma_fence_enable_sw_signaling` takes an extra reference on each chain; on error paths that `goto unwind` after at least one chain has been enabled, the unwind loop only performs a single `dma_fence_put` per chain, leaving the signaling reference leaked.
```
