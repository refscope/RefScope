# REAL BUG: net/netfilter/nft_set_hash.c:168 nft_rhash_update()

**Confidence**: HIGH | **Counter**: `$->nelems.counter`

## Reasoning

| L161 (prev==NULL → out) | success (new element inserted) | NO | NO | ❓ missing increment | new element not counted, but not an excess put; underlying bug |

## Full Response

```
| Line | Return Type | GET Done? (nelems inc) | PUT Done? (atomic_dec) | Balanced? | Notes |
|------|-------------|------------------------|------------------------|-----------|-------|
| L140–141 (goto out) | success (existing element) | NO (no nft_dynset_new) | NO | ✅ | Only uses rhashtable_lookup result; no inc/dec |
| L144–145 (goto err1) | error (nft_dynset_new returned NULL) | NO (nft_dynset_new does NOT increment nelems on failure) | NO (err1 returns without dec) | ✅ | |
| L151–152 (goto err2) | error (IS_ERR) | NO (nft_dynset_new does NOT increment nelems) | YES (atomic_dec at L166) | ❌ EXCESS PUT | dec without prior inc → nelems underflow |
| L155–158 (if(prev)) | success (race, element exists) | NO (nft_dynset_new does NOT increment nelems) | YES (atomic_dec at L157) | ❌ EXCESS PUT | dec without prior inc → nelems underflow |
| L161 (prev==NULL → out) | success (new element inserted) | NO | NO | ❓ missing increment | new element not counted, but not an excess put; underlying bug |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The `atomic_dec(&set->nelems)` calls on the error path (err2) and race path (prev exist) are excess puts because `nft_dynset_new()` does not increment `set->nelems`; only the caller is expected to manage the counter, and these paths lack a prior increment.
```
