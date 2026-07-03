# REAL BUG: drivers/md/dm-cache-target.c:1232 mg_complete()

**Confidence**: HIGH | **Counter**: `$->nr_dirty.counter`

## Reasoning

- Other paths (DEMOTE/WRITEBACK) also call `force_clear_dirty` but are not flagged by smatch, indicating that those operations already own a dirty increment that is correctly released here. The PROMOTE path without an overwrite bio does **not** own that increment, making the PUT unbalanced.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| PROMOTE, success, overwrite_bio != NULL | fall-through end | YES (force_set_dirty) | NO | ❌ (leak direction) | Warning says "excess put" not leak, so not this path |
| PROMOTE, success, overwrite_bio == NULL | fall-through end | NO | YES (force_clear_dirty at L1232) | ❌ EXCESS PUT | This is the smatch warning path – force_clear_dirty called without prior force_set_dirty |
| PROMOTE, !success, any overwrite_bio | fall-through end | NO | NO | ✅ | |
| DEMOTE, success | fall-through end | NO | YES | ✅ (external get?) | smatch not flagged; likely balanced by prior set_dirty elsewhere |
| DEMOTE, !success | fall-through end | NO | NO | ✅ | |
| WRITEBACK, success | fall-through end | NO | YES | ✅ (external get?) | same as demote |
| WRITEBACK, !success | fall-through end | NO | NO | ✅ | |

**Analysis**:
- When `op->op == POLICY_PROMOTE`, `success == true`, and `mg->overwrite_bio == NULL`, the code calls `force_clear_dirty(cache, cblock)` (PUT) without any preceding `force_set_dirty(cache, cblock)` (GET) on that path.
- The warning reports an “excess put” on `nr_dirty.counter` at the exact line of that PUT call, meaning the dirty counter would become negative.
- Other paths (DEMOTE/WRITEBACK) also call `force_clear_dirty` but are not flagged by smatch, indicating that those operations already own a dirty increment that is correctly released here. The PROMOTE path without an overwrite bio does **not** own that increment, making the PUT unbalanced.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`force_clear_dirty` called on success in PROMOTE without overwrite bio, no prior `force_set_dirty` on that path → excess put on `nr_dirty`.
```
