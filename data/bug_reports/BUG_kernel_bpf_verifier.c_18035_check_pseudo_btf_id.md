# REAL BUG: kernel/bpf/verifier.c:18035 check_pseudo_btf_id()

**Confidence**: HIGH | **Counter**: `btf->refcnt.refs.counter`

## Reasoning

| L18032 (failure) | error (<0 from __add_used_btf) | YES (btf acquired) | NO | ❌ LEAK | __add_used_btf fails, btf not released |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L18015 | error (-EINVAL) | NO (btf_get_by_fd failed) | N/A | ✅ | IS_ERR guard → no ref held |
| L18020 | error (-EINVAL) | NO (before get) | N/A | ✅ | btf_vmlinux is NULL, return early |
| L18029 | error (err) | YES (btf acquired) | YES (btf_put at L18028) | ✅ | err path after __check_pseudo_btf_id failure |
| L18032 (failure) | error (<0 from __add_used_btf) | YES (btf acquired) | NO | ❌ LEAK | __add_used_btf fails, btf not released |
| L18032 (success) | success (0) | YES | Transfer (ownership taken by used list) | ✅ | reference passed to __add_used_btf |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`__add_used_btf` can fail and does not release the owned btf; the missing `btf_put()` on that error path leaks a reference acquired via `btf_get_by_fd`/`btf_get`.
```
```
