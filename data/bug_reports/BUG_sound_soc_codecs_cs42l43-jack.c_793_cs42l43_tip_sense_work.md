# REAL BUG: sound/soc/codecs/cs42l43-jack.c:793 cs42l43_tip_sense_work()

**Confidence**: HIGH | **Counter**: `$->power.usage_count.counter`

## Reasoning

| L794 (fall through after tip!=PRESENT, condition **false** at L785) | end of function | YES (resume_and_get) | YES (L793 only) | ✅ | only one put, balanced |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L748 | return (ret!=0) | NO (resume_and_get failed) | NO | ✅ | no ref held |
| L794 (fall through after tip==PRESENT, report>=0) | end of function | YES (resume_and_get) + optional extra GET at L763 | YES (pm_runtime_put_autosuspend L793) | ✅ (only if extra GET not executed) | if extra GET done, leak – but not excess put |
| L794 (fall through after tip==PRESENT, goto error) | end of function | YES (same as above) | YES (L793) | ✅ (same condition) | not excess put |
| L794 (fall through after tip!=PRESENT, condition **true** at L784) | end of function | YES (resume_and_get) | YES (pm_runtime_put L785 **and** pm_runtime_put_autosuspend L793) | ❌ **EXCESS PUT** | double put: usage_count goes negative |
| L794 (fall through after tip!=PRESENT, condition **false** at L785) | end of function | YES (resume_and_get) | YES (L793 only) | ✅ | only one put, balanced |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On the else path (tip != PRESENT) when `cs42l43->sdw && priv->jack_present` is true, the function calls `pm_runtime_put` (L785) and then `pm_runtime_put_autosuspend` (L793) for a single initial `pm_runtime_resume_and_get`, causing an excess put.
```
