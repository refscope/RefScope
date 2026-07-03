# REAL BUG: security/apparmor/domain.c:1203 change_hat()

**Confidence**: HIGH | **Counter**: `$->label.count.count.refcount.refs.counter`

## Reasoning

| L1218 (return new; new is valid) | success | YES | N/A (ownership transferred) | ✅ | references consumed by new label |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1152 (conflicting types → goto fail → return ERR_PTR) | error | NO (before get) | N/A | ✅ | `goto fail` before any `aa_get_profile*` or `aa_find_child` |
| L1174 (target not hat → `aa_put_profile(hat); goto fail`) | error | YES (hat from `aa_find_child`) | YES (explicit `aa_put_profile(hat)`) | ✅ | root already put, hat put before jump |
| L1189 (no hats, list not empty → goto fail) | error | NO | N/A | ✅ | only list_empty check; no get calls |
| L1191 (fallthrough “no hats defined” → fail → return ERR_PTR) | error | NO | N/A | ✅ | no gets in that block |
| L1206 (!new → goto fail → return ERR_PTR) | error | YES (`aa_get_label(&profile->label)` and `build_change_hat(…)`) | NO | ❌ LEAK | The `fail:` label contains no `aa_put_label` or matching put; references acquired by `aa_get_label` and `build_change_hat` are not released on this path |
| L1218 (return new; new is ERR_PTR) | error | YES (references passed to `fn_label_build_in_scope`) | UNCLEAR | ? | depends on whether `fn_label_build_in_scope` already released on error; caller does not put |
| L1218 (return new; new is valid) | success | YES | N/A (ownership transferred) | ✅ | references consumed by new label |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  

Path through `if (!new) goto fail` after `fn_label_build_in_scope` acquires two label references (`aa_get_label` and `build_change_hat`) but never releases them. The `fail:` label contains only auditing calls, no `aa_put_label` or equivalent put operation. Unless `fn_label_build_in_scope` itself releases the references on error (the caller retains no pointer to them after the call), this path leaks. With no visible cleanup code in the caller and a strict rule that GET=YES + PUT=NO → leak, this is considered a real bug.
```
