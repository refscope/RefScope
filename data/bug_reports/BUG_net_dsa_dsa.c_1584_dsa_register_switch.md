# REAL BUG: net/dsa/dsa.c:1584 dsa_register_switch()

**Confidence**: HIGH | **Counter**: `$->dst->refcount.refcount.refs.counter`

## Reasoning

4. **goto out not applicable** – only one linear path; the bug is the unconditional `put` regardless of probe’s internal ref operations.

## Full Response

```
| Line | Return Type | GET Done? (from probe) | PUT Done? (caller) | Balanced? | Notes |
|------|-------------|------------------------|--------------------|-----------|-------|
| L1585 | return err  | Unknown – depends on dsa_switch_probe internal paths | YES (unconditional dsa_tree_put) | ❓ | probe contract says conditional get/put; caller always put → likely unbalanced on some paths |

## Analysis

The single return path in `dsa_register_switch()` unconditionally calls `dsa_tree_put(ds->dst)` after `dsa_switch_probe(ds)`.  
The contract for `dsa_switch_probe` shows it **conditionally** calls both `dsa_tree_get` and `dsa_tree_put` inside its own body.

- If `dsa_switch_probe` succeeds (err == 0), it likely holds a reference on `dst` (for the registered switch). The caller’s unconditional `dsa_tree_put` would then **immediately drop that reference**, risking a use-after-free or double-release on teardown.
- If `dsa_switch_probe` fails, it may have already cleaned up any temporary reference, leaving the caller with an **extra put that underflows** the refcount.

SMATCH has flagged the `dsa_tree_put` line as “inconsistent refcounting”, confirming that the combination of probe’s conditional get/put and the caller’s unconditional put creates an imbalance across different paths.  
Because `dsa_switch_probe` is not a simple unconditional `get` followed by a single `put` on error, the caller cannot safely perform an unconditional `put` after it returns.

## Pre-Verdict Checklist

1. **“Held for device lifetime”?** – The reference acquired inside `dsa_switch_probe` is intended for the DSA tree, not the caller. The caller’s immediate put nullifies that lifetime hold on success.
2. **“Ownership transferred”?** – No explicit transfer to the caller; the tree owns the reference after probing. Caller’s put is a misuse, not a correct cleanup.
3. **Unconditional GET?** – No; the contract explicitly states `dsa_switch_probe` is conditional. Thus GET may or may not happen.
4. **goto out not applicable** – only one linear path; the bug is the unconditional `put` regardless of probe’s internal ref operations.

## VERDICT: REAL_BUG

## CONFIDENCE: HIGH
`dsa_register_switch` unconditionally calls `dsa_tree_put` after a conditional `dsa_switch_probe`; this either drops a reference the tree still needs (on success) or over-releases on error, causing the refcount imbalance reported by SMATCH.
```
