# REAL BUG: sound/core/pcm_native.c:2248 snd_pcm_drain()

**Confidence**: HIGH | **Counter**: `$->refs.refs.counter`

## Reasoning

| L2228 | break (tout timeout) | Conditional (get at L2206 may fail) | YES (unref L2215 always called) | ❌ LEAK if get failed; balanced if get succeeded | same as above |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2136 | return -EBADFD | NO (before any get) | N/A | ✅ | get hasn't happened yet |
| L2157 | goto unlock | NO (before any get) | N/A | ✅ | get hasn't happened yet |
| L2162 | goto unlock | NO (before any get) | N/A | ✅ | get hasn't happened yet |
| L2174 | break (signal_pending) | NO (before get in this iteration) | N/A | ✅ | no get called on this path |
| L2186 | break (all drained) | Conditional (get at L2176 may fail) | YES (unref L2185 always called) | ❌ LEAK if get failed; balanced if get succeeded | get result not checked; unconditional unref |
| L2217 | break (card->shutdown) | Conditional (get at L2206 may fail) | YES (unref L2215 always called) | ❌ LEAK if get failed; balanced if get succeeded | get result not checked; unconditional unref |
| L2228 | break (tout timeout) | Conditional (get at L2206 may fail) | YES (unref L2215 always called) | ❌ LEAK if get failed; balanced if get succeeded | same as above |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  

`snd_pcm_stream_group_ref` is a conditional get (may not increment refcount), yet `snd_pcm_drain` always calls `snd_pcm_group_unref` without checking whether the get succeeded. On paths where the get fails, the unconditional put causes an excess decrement, leading to the reported refcount inconsistency.
```
