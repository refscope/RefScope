# REAL BUG: drivers/of/base.c:1018 of_find_node_opts_by_path()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

returns NULL | YES (of_find_node_by_path gave ref) | NO (__of_find_node_by_full_path does not put on early mismatch) | ❌ LEAK | Alias resolution gives a reference. When the subsequent path step fails, __of_find_node_by_full_path returns NULL without releasing the input reference → refcount leak. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L982 | success (return of_node_get(of_root)) | YES (of_node_get) | N/A (passed to caller) | ✅ | Ref transferred to caller, no internal leak. |
| L995 | error (return NULL after !of_aliases) | NO (no get executed) | N/A | ✅ | No reference held. |
| L1005 | error (return NULL after alias loop, np == NULL) | NO (np NULL) | N/A | ✅ | No reference held. |
| L1014 | success/error (return np from __of_find_node_by_full_path) — np from of_node_get(of_root) path | YES (of_node_get) | YES (consumed by __of_find_node_by_full_path success or failure) | ✅ | __of_find_node_by_full_path takes ownership of the input reference; if it fails, it still releases it. |
| L1014 | success (return np) — np from alias, __of_find_node_by_full_path success | YES (of_find_node_by_path gave ref) | YES (consumed by __of_find_node_by_full_path, returns new ref) | ✅ | Old ref consumed, new ref returned. |
| L1014 | error (return NULL) — np from alias, __of_find_node_by_full_path returns NULL | YES (of_find_node_by_path gave ref) | NO (__of_find_node_by_full_path does not put on early mismatch) | ❌ LEAK | Alias resolution gives a reference. When the subsequent path step fails, __of_find_node_by_full_path returns NULL without releasing the input reference → refcount leak. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
When an alias is resolved, `of_find_node_by_path` acquires a reference on the target node. If the remaining path after the alias does not match the node’s full name, `__of_find_node_by_full_path` fails and returns NULL without releasing the input reference, leaking the alias node’s refcount.
```
