# REAL BUG: kernel/bpf/bpf_struct_ops.c:1133 bpf_struct_ops_map_alloc()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| ~1120 (return map, success) | success | YES | transferred to map (st_map->btf) | ✅ | map holds btf, released when map is freed |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~1060 (fd branch, IS_ERR) | error | NO | N/A | ✅ | IS_ERR guard before get success |
| ~1062 (fd branch, !btf_is_module) | error | YES (btf_get_by_fd) | YES (btf_put before return) | ✅ | explicit put, balanced |
| ~1069 (fd branch, !mod) | error | NO (btf_put already done) | N/A | ✅ | btf ref already dropped |
| ~1074 (vmlinux branch, IS_ERR) | error | NO | N/A | ✅ | IS_ERR guard, no ref held |
| ~1075 (vmlinux branch, !btf) | error | NO (get failed, NULL) | N/A | ✅ | NULL return, no ref |
| ~1081 (goto errout – no st_ops_desc) | error | YES (bpf_get_btf_vmlinux) | NO | ❌ LEAK | errout only does module_put(mod), no btf_put |
| ~1087 (goto errout – size mismatch) | error | YES | NO | ❌ LEAK | |
| ~1099 (goto errout – st_map alloc fail) | error | YES | NO | ❌ LEAK | |
| ~1113 (goto errout_free – uvalue/links/ksyms fail) | error | YES | NO | ❌ LEAK | errout_free calls __bpf_struct_ops_map_free, but st_map->btf not yet set; then errout without btf_put |
| ~1120 (return map, success) | success | YES | transferred to map (st_map->btf) | ✅ | map holds btf, released when map is freed |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`bpf_get_btf_vmlinux()` acquires a reference on the vmlinux BTF. All error paths after that call (goto errout / errout_free) fail to call `btf_put()`, leaking the refcount. Only the fd branch explicitly releases its btf ref before error returns.
```
