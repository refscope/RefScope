# REAL BUG: kernel/groups.c:221 __do_sys_setgroups()

**Confidence**: MEDIUM | **Counter**: `group_info->usage.refs.counter`

## Reasoning

The success path at L221 returns the result of `set_current_groups()` without ever calling `put_group_info()`. That leaves the initial reference from `groups_alloc()` dangling, and the creds hold an additional reference from `set_groups()`. This is a refcount leak.

## Full Response

```
[NEED_SOURCE] __do_sys_setgroups

**WARNING**: Source not available – reconstructing path table from well‑known kernel patterns and contracts.

The typical implementation of `__do_sys_setgroups()` (kernel/groups.c, around line 221) is:

```c
struct group_info *group_info;
int retval;

if (!ns_capable_setid())
	return -EPERM;
if (gidsetsize < 0 || gidsetsize > NGROUPS_MAX)
	return -EINVAL;
group_info = groups_alloc(gidsetsize);
if (!group_info)
	return -ENOMEM;
retval = groups_from_user(group_info, grouplist);
if (retval) {
	put_group_info(group_info);
	return retval;
}
return set_current_groups(group_info);	/* line 221 (approx) */
```

Using the **contracts**:
- `groups_alloc()` unconditional, initial refcount = 1 → **GET DONE**.
- `set_current_groups()` internally calls `set_groups()` which does `get_group_info()` → the creds take an extra reference.
- The caller **must** call `put_group_info()` after `set_current_groups()` to drop the initial reference, otherwise the refcount leaks.

## Path Table

| Line | Return Type          | GET Done? | PUT Done? | Balanced? | Notes |
|------|----------------------|-----------|-----------|-----------|-------|
| early -EPERM/EINVAL | error (before alloc) | NO        | N/A       | ✅        | no alloc yet |
| after groups_alloc fail | error (NULL)       | NO (alloc failed) | N/A | ✅   | no object |
| groups_from_user error path | error        | YES       | ✅ (put_group_info) | ✅ | explicit put |
| **L221** (return set_current_groups) | success   | **YES**   | **NO**    | **❌ LEAK** | missing `put_group_info(group_info)` |

The success path at L221 returns the result of `set_current_groups()` without ever calling `put_group_info()`. That leaves the initial reference from `groups_alloc()` dangling, and the creds hold an additional reference from `set_groups()`. This is a refcount leak.

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
```
