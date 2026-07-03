# REAL BUG: net/ipv4/fib_trie.c:1392 fib_table_insert()

**Confidence**: HIGH | **Counter**: `$->fib_clntref.refs.counter`

## Reasoning

`fib_release_info` only decrements `fib_treeref` (the trie’s reference). On error paths, the code calls `fib_release_info(fi)` but does **not** call `fib_info_put` or any function that drops `fib_clntref`. Therefore, `fib_clntref` is leaked on every error path after `fib_create_info` succeeds.

## Full Response

```
## PATH TABLE

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1207 (goto err) | error (IS_ERR) | NO (IS_ERR) | N/A | ✅ | No fib_info allocated |
| L1240 (goto out) | error (-EEXIST, NLM_F_EXCL) | YES | NO for `fib_clntref` | ❌ LEAK | `out:` only calls `fib_release_info` (drops `fib_treeref`); `fib_clntref` leaked |
| L1252 (goto out) | error (-ENOBUFS, !new_fa) | YES | NO for `fib_clntref` | ❌ LEAK | same |
| L1268 (goto out_free_new_fa) | error in notifier | YES | NO for `fib_clntref` | ❌ LEAK | `out_free_new_fa -> out:` path drops `fib_treeref` only |
| L1280 (goto succeeded) | success (replace) | YES | N/A (transferred) | ✅ | fib_info owned by alias |
| L1290 (goto out) | fa_match | YES | NO for `fib_clntref` | ❌ LEAK | |
| L1294 (goto out) | !NLM_F_CREATE | YES | NO for `fib_clntref` | ❌ LEAK | |
| L1300 (goto out) | !new_fa | YES | NO for `fib_clntref` | ❌ LEAK | |
| L1324 (goto out_free_new_fa) | fib_insert_alias err | YES | NO for `fib_clntref` | ❌ LEAK | |
| L1329 (goto out_free_new_fa) | WARN_ON(!l) | YES | NO for `fib_clntref` | ❌ LEAK | |
| L1340 (goto out_remove_new_fa) | notifier err after insert | YES | NO for `fib_clntref` | ❌ LEAK | calls `fib_remove_alias` then falls through to `out:` – `fib_clntref` still leaked |
| L1350 (goto succeeded) | success | YES | N/A (transferred) | ✅ | owned by alias |

**NOTE**: `fib_create_info` initializes both `fib_treeref` and `fib_clntref` to 1. `fib_release_info` only decrements `fib_treeref` (the trie’s reference). On error paths, the code calls `fib_release_info(fi)` but does **not** call `fib_info_put` or any function that drops `fib_clntref`. Therefore, `fib_clntref` is leaked on every error path after `fib_create_info` succeeds.

## VERDICT: REAL_BUG
## CONFIDENCE: HIGH
`fib_create_info` returns `fib_info` with both `fib_treeref` and `fib_clntref` held. Error paths only release `fib_treeref` via `fib_release_info`, leaking `fib_clntref`. Success path transfers ownership, but all error exits leave `fib_clntref` leaked.
```
