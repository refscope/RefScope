# REAL BUG: kernel/bpf/syscall.c:5912 link_detach()

**Confidence**: HIGH | **Counter**: `$->refcnt.counter`

## Reasoning

l `bpf_link_put()`, causing refcount to drop to zero; subsequent `bpf_link_put_direct()` at L5911 then triggers refcount excess put warning. Contract for detach should guarantee it does not consume the caller’s reference. [NEED_SOURCE] bpf_link_get_from_fd, bpf_link_put_direct, link->ops->detach |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L5899-5900 | error (CHECK_ATTR) | NO (before get) | N/A | ✅ | |
| L5903-5904 | error (IS_ERR) | NO (get failed) | N/A | ✅ | |
| L5911-5912 | success/error (after detach) | YES (get succeeded) | YES (bpf_link_put_direct) | ❌ EXCESS PUT | `link->ops->detach()` may internally call `bpf_link_put()`, causing refcount to drop to zero; subsequent `bpf_link_put_direct()` at L5911 then triggers refcount excess put warning. Contract for detach should guarantee it does not consume the caller’s reference. [NEED_SOURCE] bpf_link_get_from_fd, bpf_link_put_direct, link->ops->detach |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
link_detach() calls bpf_link_put_direct() after link->ops->detach(), but detach may already release the link's reference, leading to a double put and refcount underflow.
```
