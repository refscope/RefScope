# REAL BUG: fs/nfsd/nfsctl.c:386 write_filehandle()

**Confidence**: HIGH | **Counter**: `dom->ref.refcount.refs.counter`

## Reasoning

| L.. (success return mesg - buf) | success | YES | (already put at L386) | As above | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L.. (early size checks) | error (-EINVAL) | NO (before get) | N/A | ✅ | |
| L.. (buf[size-1] != '\n') | error (-EINVAL) | NO | N/A | ✅ | |
| L.. (dname len <= 0) | error (-EINVAL) | NO | N/A | ✅ | |
| L.. (path len <= 0) | error (-EINVAL) | NO | N/A | ✅ | |
| L.. (get_int len) | error (len) | NO | N/A | ✅ | |
| L.. (maxsize < NFS_FHSIZE) | error (-EINVAL) | NO | N/A | ✅ | |
| L.. (qword_get > 0) | error (-EINVAL) | NO | N/A | ✅ | |
| L378 (dom = unix_domain_find) | GET (unconditional per contract) | YES | No put yet | – | Ref acquired |
| L.. (if (!dom) return -ENOMEM) | error (-ENOMEM) | NO (NULL, no ref) | N/A | ✅ | Conditional; no ref held |
| L.. (exp_rootfh call) | – | YES | – | – | After call, dom may be put by exp_rootfh? |
| L386 (auth_domain_put(dom)) | successful/error (after put) | YES | YES | **❌ Excess if exp_rootfh also put** | Smatch warns excess put here |
| L387 (if (len) return len) | error (len) | YES | (already put at L386) | As above | |
| L.. (success return mesg - buf) | success | YES | (already put at L386) | As above | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`exp_rootfh` likely consumes the auth_domain reference (calls `auth_domain_put` internally); the explicit `auth_domain_put(dom)` at L386 then causes a double-put, flagged as “refcount excess put.”
```
