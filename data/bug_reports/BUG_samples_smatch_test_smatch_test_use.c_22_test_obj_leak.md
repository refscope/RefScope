# REAL BUG: samples/smatch_test/smatch_test_use.c:22 test_obj_leak()

**Confidence**: HIGH | **Counter**: `$->refs.refs.counter`

## Reasoning

| L22  | error       | YES      | NO   | ❌ LEAK | fallthrough error path, no put |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L14  | error       | NO (get returned NULL) | N/A | ✅ | !o → no ref held |
| L18  | error       | YES      | YES  | ✅ | put called before return |
| L22  | error       | YES      | NO   | ❌ LEAK | fallthrough error path, no put |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
test_obj_get() succeeds at L11, but L22 return -EFAULT skips test_obj_put causing refcount leak.
```
