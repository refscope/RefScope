# REAL BUG: kernel/cgroup/cgroup.c:7002 cgroup_post_fork()

**Confidence**: MEDIUM | **Counter**: `$->refcount.refs.counter`

## Reasoning

fcount was already zero, meaning the caller did **not** properly hand over a live reference. This is a bug in the interaction – either the caller failed to acquire the expected reference, or cgroup_post_fork() should not unconditionally put on that path. Therefore, the reported excess put is real.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~6950 (child->pid == 0) | (init task path) | No explicit get; relies on caller’s reference from kargs->cset | YES (put_css_set(cset)) | ❌ Potential excess put if caller’s reference already zero | Warning indicates the passed refcount was already zero, causing an excess put. |
| ~6955 (child->pid != 0) | (non‑init path) | No get; reference transferred to child via css_set_move_task | NO | ✅ | Reference remains with child, no put needed. |
| ~6976 (CLONE_NEWCGROUP) | get_css_set(cset) unconditional | YES | No immediate put; deferred via namespace cleanup | ✅ | Extra reference held by cgroup ns, balanced outside this function. |
| ~6999 (end, via cgroup_css_set_put_fork) | (post‑fork cleanup) | Dependent on kargs state; kargs->cset already NULL → no cset get/put here | Possibly other puts not related to cset? | ℹ️ | Need callee source to assess. |

The excess‑put warning is on line 7002, which, in the full file, matches the `put_css_set(cset)` inside the `child->pid == 0` branch. That branch assumes a valid reference was provided by the caller. The warning indicates the refcount was already zero, meaning the caller did **not** properly hand over a live reference. This is a bug in the interaction – either the caller failed to acquire the expected reference, or cgroup_post_fork() should not unconditionally put on that path. Therefore, the reported excess put is real.

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
Reasoning: On init‑task path, cgroup_post_fork performs put_css_set(cset) assuming kargs->cset held a valid reference, but the refcount was already zero, indicating a missing get in the caller or an incorrect reference hand-off.
```
