# REAL BUG: fs/ocfs2/buffer_head_io.c:187 ocfs2_read_blocks_sync()

**Confidence**: HIGH | **Counter**: `$->b_count.counter`

## Reasoning

| L167 (first bh fails to become uptodate, status=-EIO via L162) | -EIO | YES on all non-JBD submitted | same as above, L149 executed on non-JBD bhs | ❌ **excess put** on dirty bhs | dirty bh (L124-125) can be put erroneously |

## Full Response

```
| Path Description | Status | GET Done? | PUT Done? | Balanced? | Notes |
|------------------|--------|-----------|-----------|-----------|-------|
| L99 (goto bail, nr==0) | 0 | None | None | ✅ | No buffers processed |
| L167 (normal success, all bhs uptodate) | 0 | YES on all non-JBD bhs submitted (L136) | No put in cleanup loop (L157-163) | ✅ (no excess) | end_io will put; cleanup does not put on success |
| L167 (error during submission, e.g. ENOMEM at L113, status != 0) | -ENOMEM | YES on earlier non-JBD, non-dirty bhs (L136) | put_bh called on all allocated non-JBD bhs (L149) | ❌ **excess put** on any dirty bh that was skipped at L124-125 and later gets put via L149 | L149 puts a dirty bh that never had get_bh |
| L167 (first bh fails to become uptodate, status=-EIO via L162) | -EIO | YES on all non-JBD submitted | same as above, L149 executed on non-JBD bhs | ❌ **excess put** on dirty bhs | dirty bh (L124-125) can be put erroneously |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`put_bh` on error path does not account for dirty buffers that skipped `get_bh`; causes excess put.
```
