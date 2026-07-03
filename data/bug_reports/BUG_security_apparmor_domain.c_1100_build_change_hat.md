# REAL BUG: security/apparmor/domain.c:1100 build_change_hat()

**Confidence**: HIGH | **Counter**: `$->label.count.count.refcount.refs.counter`

## Reasoning

| return &hat->label (L1100) (COMPLAIN_MODE, learning succeed, hat!=NULL) | success | YES (aa_new_learning_profile succeeded) | NO (no aa_put_profile/aa_free_profile) | ❌ LEAK | hat refcount 1, never released; label refcount leaks with it |

## Full Response

```
| Line | Return Type | GET (hat) Done? | PUT (hat) Done? | Balanced? | Notes |
|------|-------------|-----------------|-----------------|-----------|-------|
| goto audit (L1082) + return ERR_PTR (L1098) | error (-EPERM) | NO (before get) | N/A | ✅ | hat=NULL, root not obtained |
| return &hat->label (L1100) (hat found via aa_find_child) | success | NO (borrowed) | N/A (no get) | ✅ | hat is a non‑owning pointer, root put |
| return ERR_PTR(-ENOENT) (L1098) (not COMPLAIN_MODE, hat=NULL) | error | NO | N/A | ✅ | no hat created |
| return ERR_PTR(-ENOMEM) (L1098) (COMPLAIN_MODE, learning fail, hat=NULL) | error | NO (get failed) | N/A | ✅ | aa_new_learning_profile returned NULL |
| return &hat->label (L1100) (COMPLAIN_MODE, learning succeed, hat!=NULL) | success | YES (aa_new_learning_profile succeeded) | NO (no aa_put_profile/aa_free_profile) | ❌ LEAK | hat refcount 1, never released; label refcount leaks with it |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Missing `aa_put_profile(hat)` on the successful learning‑profile path after returning `&hat->label`; the profile (and its embedded label) is leaked.
```
