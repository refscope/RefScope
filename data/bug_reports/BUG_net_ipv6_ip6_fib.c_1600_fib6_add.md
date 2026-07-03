# REAL BUG: net/ipv6/ip6_fib.c:1600 fib6_add()

**Confidence**: HIGH | **Counter**: `$->fib6_ref.refs.counter`

## Reasoning

detected by smatch at line 1600 (the `failure:` label’s `return err;`) matches the path where a reference was acquired (`fib6_info_hold(null_entry)`) but never released before returning. The `node_free_immediate` call only frees the memory; it does not call `fib6_info_release` on the leaf pointer.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| After first `fib6_add_1()` (IS_ERR(fn)) → `goto out` → `failure` | Error | N/A | N/A | ✅ | No `fib6_info_hold` calls yet; input `rt` still owned by caller. |
| `sfn = node_alloc()` fails → `goto failure` | Error | N/A | N/A | ✅ | Subtree root creation not attempted. |
| `sn = fib6_add_1(...)` inside subtree block fails → `node_free_immediate(sfn)` + `goto failure` | Error | **YES** – `fib6_info_hold(null_entry)` at `sfn->leaf` assignment | **NO** | ❌ **LEAK** | `null_entry` refcount increased, but never released before freeing `sfn`. |  
| `fib6_add_rt2node*` fails (after subtree block) → `out:` → `failure` | Error | **YES** – possible `fib6_info_hold(rt)` if `fn->leaf` was NULL (L5), plus unknown holds from `fib6_add_rt2node*` | Partially – `out:` block releases `rt` via `fib6_info_release(rt)` if `pn->leaf == rt`. | ⚠️ Depends on callee internals | The extra `rt` hold from L5 is correctly undone, but if `fib6_add_rt2node*` acquired internal refs and failed, those may need explicit release (source not provided). |
| `fib6_add_rt2node*` succeeds → `out:` (err==0) → return | Success | Holds on `null_entry` (subtree root), possibly `rt` (via L5), plus holds from `fib6_add_rt2node*` | No explicit puts needed | ✅ | Refs belong to tree – correctly transferred lifetime, cleaned up on route deletion. |

### Path‑by‑path reasoning

- **First `fib6_add_1` error**: No `fib6_info_hold` or route insertion attempted, no ref acquired on any object.  
- **`sfn` allocation failure**: Before any `hold`, so no imbalance.  
- **`sn` error inside subtree creation**: `fib6_info_hold(null_entry)` was called unconditionally on the null entry, and the pointer stored in `sfn->leaf`. On error, `node_free_immediate(net, sfn)` is called, but the leaf reference is not dropped. The subtree root is never linked into the main tree, so the reference leaked will never be released. This is an explicit refcount leak.  
- **`fib6_add_rt2node*` error**:  
  - If the subtree block assigned `rt` to `fn->leaf` (i.e., `fib6_info_hold(rt)` was called), the out‑block logic correctly detects `pn->leaf == rt` and calls `fib6_info_release(rt)`, balancing that extra hold.  
  - However, the semantics of `fib6_add_rt2node*` with respect to internal reference counting are unknown. The probe does not have its source; if it takes an unconditional reference and fails without releasing it, a leak could occur. But the provided code already contains a clear, independently demonstrable leak on the `sn` error path.  
- **Full success path**: All held references become part of the fib tree and are properly released at route deletion.

**Why the warning is consistent with this leak**  
The inconsistent refcounting detected by smatch at line 1600 (the `failure:` label’s `return err;`) matches the path where a reference was acquired (`fib6_info_hold(null_entry)`) but never 
```
