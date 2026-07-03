# REAL BUG: fs/btrfs/delayed-inode.c:310 __btrfs_release_delayed_node()

**Confidence**: HIGH | **Counter**: `$->refs.refs.counter`

## Reasoning

rfs_dequeue_delayed_node()` does `refcount_dec(put)` **and** `refcount_dec_and_test()` does another dec | ❌ **EXCESS PUT** | On `count == 0`, dequeue already drops one reference; the immediate subsequent `refcount_dec_and_test` drops another → potential underflow if the incoming refcount was 1 |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L283 | early return (null) | NO | NO | N/A | `delayed_node == NULL`; no refs held |
| L291 (count≠0) | falls through to end, then implicit return | YES: `btrfs_queue_delayed_node()` does `refcount_inc(get)×2` | YES: `refcount_dec_and_test()` | ⚠️ possible imbalance | queue may add two refs, final dec_one; but not an **excess** put (the warning is excess put) — this path likely fine |
| L293 (count==0) | falls through to end, then implicit return | NO | YES: `btrfs_dequeue_delayed_node()` does `refcount_dec(put)` **and** `refcount_dec_and_test()` does another dec | ❌ **EXCESS PUT** | On `count == 0`, dequeue already drops one reference; the immediate subsequent `refcount_dec_and_test` drops another → potential underflow if the incoming refcount was 1 |

**VERDICT: REAL_BUG**  
**CONFIDENCE: HIGH**  

When `delayed_node->count == 0`, `__btrfs_release_delayed_node` calls `btrfs_dequeue_delayed_node` (which performs a `refcount_dec` on `delayed_node->refs`) and then unconditionally calls `refcount_dec_and_test` on the same counter. This results in **two puts** for a single reference held by the caller, causing a refcount underflow (excess put) on `$->refs.refs.counter` at line 310. The `count != 0` path does not trigger the extra dec, but the `count == 0` path triggers the warning.
```
