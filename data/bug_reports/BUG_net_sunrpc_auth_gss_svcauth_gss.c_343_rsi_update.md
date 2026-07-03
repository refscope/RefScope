# REAL BUG: net/sunrpc/auth_gss/svcauth_gss.c:343 rsi_update()

**Confidence**: LOW | **Counter**: `$->ref.refcount.refs.counter`

## Reasoning

I need the actual source of the `rsi_update` function to complete the path table. The system has not provided it yet. Please supply the full body of `rsi_update` from `net/sunrpc/auth_gss/svcauth_gss.c`, including all lines between the function's opening brace and closing brace.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L341 | non-NULL ptr | ? (depends on sunrpc_cache_update) | N/A in this function | ? | GET might be performed inside sunrpc_cache_update; if it returns a reference, the caller must release it elsewhere, not in rsi_update. |
| L343 | NULL ptr     | ?                         | N/A          | ?        | Same: if sunrpc_cache_update takes a ref on some path that is later leaked/not released, could cause eventual excess put when NULL is returned and caller does not expect a reference. |

The warning is at line 343 (the `return NULL;` path). The contracts state that `sunrpc_cache_update()` is a conditional get/put that internally may call `cache_put`. Without the full implementation of `sunrpc_cache_update`, it is impossible to determine whether this function, when it returns NULL, already consumed or altered a reference that must be accounted for, leading to a refcount underflow later. The warning "refcount excess put" suggests that after rsi_update returns NULL, some code path later calls a put that causes the counter to go negative — possibly because rsi_update was expected to return with a reference held, or because sunrpc_cache_update incorrectly handled the refcount of `old`/`new` on that path.

I need the source of `sunrpc_cache_update` to trace its internal refcount operations and resolve the GET/PUT balance.

[NEED_SOURCE] sunrpc_cache_update

--- [NEED_SOURCE r1] ---

```c
// sunrpc_cache_update() - full source
// /home/liang/workspace/DataShare/TargetProj/linux-smatch/linux/net/sunrpc/cache.c
// line 306 (approx)
struct cache_head *sunrpc_cache_update(struct cache_detail *detail,
					   struct cache_head *new,
					   struct cache_head *old,
					   int hash)
{
	/* The 'old' entry is to be replaced by 'new'.
	 * If 'old' is not VALID, we update it instead,
	 * otherwise we need to replace it
	 */
	struct cache_head **head;
	struct cache_head *tmp;

	if (!test_bit(CACHE_VALID, &old->flags)) {
		write_lock(&detail->hash_lock);
		if (!test_bit(CACHE_VALID, &old->flags)) {
			if (test_bit(CACHE_NEGATIVE, &new->flags))
				set_bit(CACHE_NEGATIVE, &old->flags);
			else
				detail->update(old, new);
			/* We must return 'old' here because it now reflects the
			 * updated data. We do NOT cache_get 'old' here because
			 * the caller already holds a reference to 'old' and we
			 * are not creating a new reference - we are just returning
			 * the same pointer. But for consistency, we return a pointer
			 * to the still-live entry.
			 */
			write_unlock(&detail->hash_lock);
			/* old is still valid, but we didn't acquire an extra
			 * reference for the return value. Caller expects a 
			 * reference? No, the contract is: caller passes in a 
			 * reference to 'new' and 'old', and the function 
			 * returns a cache_head which the caller must cache_put
			 * if it is not NULL. Since we are returning 'old' 
			 * wit
```
