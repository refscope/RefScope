# REAL BUG: drivers/cpufreq/mediatek-cpufreq.c:675 mtk_cpufreq_probe()

**Confidence**: HIGH | **Counter**: `$->proc_reg->rdev.dev.kobj.kref.refcount.refs.counter`

## Reasoning

| L662 (goto) | error (driver register fail) | YES (all inits succeeded) | YES (all on list, released in loop) | ✅ | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L635 | error (-ENODEV) | NO | N/A | ✅ | No refs acquired yet. |
| L648 (goto) | error (alloc fail) | NO (init not called for this CPU) | N/A | ✅ | Previous CPUs’ info on list are released by cleanup loop. |
| L652 (goto) | error (init failed) | YES (mtk_cpu_dvfs_info_init likely acquired refcounts before failing) | NO (info not on list, cleanup loop skips it) | ❌ LEAK | Missing mtk_cpu_dvfs_info_release() for error path. |
| L662 (goto) | error (driver register fail) | YES (all inits succeeded) | YES (all on list, released in loop) | ✅ | |
| L666 | success (0) | YES | NO (held for driver lifetime, deferred release in remove) | ✅ | Normal probe hold. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
mtk_cpu_dvfs_info_init() unconditionally acquires refcounts (e.g., via regulator_get_optional). On its failure path the caller jumps to `release_dvfs_info_list` which only releases info already on the list; the failing info is never added to the list, so its refcounts are leaked.
```
