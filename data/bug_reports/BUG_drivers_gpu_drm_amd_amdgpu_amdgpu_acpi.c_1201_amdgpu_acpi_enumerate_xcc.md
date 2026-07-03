# REAL BUG: drivers/gpu/drm/amd/amdgpu/amdgpu_acpi.c:1201 amdgpu_acpi_enumerate_xcc()

**Confidence**: HIGH | **Counter**: `acpi_dev->dev.kobj.kref.refcount.refs.counter`

## Reasoning

| L1201 | return 0 (end of function) | NO (acpi_dev NULL in last iteration or loop completed, final put done) | N/A | ✅ | Normal exit, all puts handled |

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1166 | break → L1201 return 0 | NO (acpi_dev == NULL) | N/A | ✅ | No acpi device found |
| L1171 | return -ENOMEM | YES (acpi_dev != NULL) | NO | ❌ LEAK | acpi_dev_get ref held, never released |
| L1190 | return -ENOMEM | NO (already put at L1175) | N/A (put done) | ✅ | After acpi_dev_put |
| L1201 | return 0 (end of function) | NO (acpi_dev NULL in last iteration or loop completed, final put done) | N/A | ✅ | Normal exit, all puts handled |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`acpi_dev_get_first_match_dev` unconditional get at L1159; if `xcc_info` allocation fails (L1169–L1171), `acpi_dev_put` is never called, leaking the reference.
```
