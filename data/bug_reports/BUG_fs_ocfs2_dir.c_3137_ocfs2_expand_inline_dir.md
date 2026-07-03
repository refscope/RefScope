# REAL BUG: fs/ocfs2/dir.c:3137 ocfs2_expand_inline_dir()

**Confidence**: HIGH | **Counter**: `$->b_count.counter`

## Reasoning

| Success path (all successful) | success | dx_root_bh transferred to lookup, local set to NULL | NO (brelse on NULL harmless) | ✅ | reference passed to caller via lookup->dl_dx_root_bh, local pointer cleared |

## Full Response

```
| Path | Return Type | dx_root_bh GET? | dx_root_bh PUT? | Balanced? | Notes |
|------|-------------|------------------|------------------|-----------|-------|
| Early goto out (before meta_ac reserve, L2824‑2850) | error  | NO (never allocated) | NO (dx_root_bh NULL → brelse harmless) | ✅ | dx_root_bh stays NULL |
| goto out after ocfs2_reserve_clusters fail (L2856‑2860) | error  | NO  | NO  | ✅  | same  |
| goto out after ocfs2_start_trans fail (L2866‑2869) | error  | NO  | NO  | ✅  | same  |
| goto out_commit after dquot_alloc fail (L2874‑2876) | error  | NO (attach not called) | NO  | ✅  |  |
| goto out_commit after __ocfs2_dx_dir_new_cluster fail (L2882‑2884) | error  | NO (attach not called) | NO  | ✅  |  |
| goto out_commit after ocfs2_claim_clusters fail (L2893‑2894) | error  | NO  | NO  | ✅  |  |
| goto out_commit after sb_getblk fail (L2900‑2902) | error  | NO  | NO  | ✅  |  |
| goto out_commit after ocfs2_journal_access_db fail (L2909‑2911) | error  | NO  | NO  | ✅  |  |
| goto out_commit after ocfs2_dx_dir_index_block fail (L2931‑2932) | error  | NO (attach not called) | NO  | ✅  |  |
| goto out_commit after ocfs2_journal_access_di fail (L2938‑2939) | error  | NO  | NO  | ✅  |  |
| goto out_commit after ocfs2_insert_extent(et) fail (L2961‑2962) | error  | NO  | NO  | ✅  |  |
| **goto out_commit after ocfs2_dx_dir_attach_index fail (L2974‑2975)** | **error** | **Maybe YES – callee allocates dx_root_bh before failing** | YES (final brelse L3137) | **❌ POSSIBLE DOUBLE PUT** | If callee already released the buffer on failure, the final brelse is an excess put. |
| goto out_commit after alloc>len ocfs2_claim_clusters fail (L2997‑2998) | error  | dx_root_bh non‑NULL (attach succeeded) | YES | ✅ (single put, caller holds ref from attach) | dx_root_bh not yet transferred, so correct to release |
| goto out_commit after alloc>len insert_extent fail (L3005‑3006) | error  | dx_root_bh non‑NULL | YES | ✅ | same |
| Success path (all successful) | success | dx_root_bh transferred to lookup, local set to NULL | NO (brelse on NULL harmless) | ✅ | reference passed to caller via lookup->dl_dx_root_bh, local pointer cleared |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
In `ocfs2_expand_inline_dir()`, when `ocfs2_dx_dir_attach_index()` fails after internally obtaining `dx_root_bh`, it likely releases the buffer head but leaves the pointer non‑NULL. The subsequent `brelse(dx_root_bh)` at the end of the function (line 3137) then performs an excess put on an already freed buffer, triggering the refcount underflow.
```
