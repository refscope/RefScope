# REAL BUG: fs/nfsd/filecache.c:894 __nfsd_file_cache_purge()

**Confidence**: LOW | **Counter**: `$->nf_ref.refs.counter`

## Reasoning

it | Unknown (nfsd_file_cond_queue may or may not take reference) | Yes (dispose_list calls put on each cached nf) | ❌ LEAK (excess put) | The dispose_list put triggers a refcount underflow, implying cond_queue did not grab a reference. The bug is a missing get before adding to the dispose list. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| After loop, nfsd_file_dispose_list call (line 894) | void function exit | Unknown (nfsd_file_cond_queue may or may not take reference) | Yes (dispose_list calls put on each cached nf) | ❌ LEAK (excess put) | The dispose_list put triggers a refcount underflow, implying cond_queue did not grab a reference. The bug is a missing get before adding to the dispose list. |

VERDICT: REAL_BUG
CONFIDENCE: LOW

The warning reports an excess put on `nf->nf_ref.refs.counter` inside `nfsd_file_dispose_list()`. Since `nfsd_file_cond_queue()` is the only GET candidate and its contract is unknown, the imbalance suggests it failed to take a reference before adding the file to `dispose`, leading to an underflow when `dispose_list` unconditionally releases it.
```
