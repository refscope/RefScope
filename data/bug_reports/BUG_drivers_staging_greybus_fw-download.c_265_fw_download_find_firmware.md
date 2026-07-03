# REAL BUG: drivers/staging/greybus/fw-download.c:265 fw_download_find_firmware()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| L264 | success, 0 | YES (unconditional get) | NO | ❌ LEAK | no release of fw_req ref |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L233 | error, -EINVAL | NO (before find_firmware) | N/A | ✅ | size check |
| L244 | error, -EINVAL | NO (before find_firmware) | N/A | ✅ | tag null-termination check |
| L249 | error, PTR_ERR(fw_req) | NO (IS_ERR guard; get failed) | N/A | ✅ | no ref held |
| L254 | error, -ENOMEM | YES (unconditional get, fw_req valid) | YES (free_firmware called) | ✅ | correct cleanup |
| L264 | success, 0 | YES (unconditional get) | NO | ❌ LEAK | no release of fw_req ref |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Success path (return 0) does not call free_firmware, leaking the kref acquired by the unconditional find_firmware. The warning mislabels the issue as an excess put, but the actual bug is a missing put on success.
```
