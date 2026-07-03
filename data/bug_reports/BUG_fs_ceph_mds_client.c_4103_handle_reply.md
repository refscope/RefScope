# REAL BUG: fs/ceph/mds_client.c:4103 handle_reply()

**Confidence**: MEDIUM | **Counter**: `$->r_kref.refcount.refs.counter`

## Reasoning

| YES | YES (out put at ~4103) | ⚠️ depends on complete_request | **complete_request(mdsc, req)** is called at ~4098, before final put. If complete_request internally calls ceph_mdsc_put_request(), the out put becomes an excess put (refcount already zero). That matches the warning at line 4103. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~3910 (short reply) | return | NO (before lookup_get_request) | N/A | ✅ | |
| ~3916 (tid not found) | return | NO | N/A | ✅ | |
| ~3925 (session mismatch) | goto out | YES | YES (via out) | ✅ | |
| ~3932 (dup reply/unsafe) | goto out | YES | YES | ✅ | |
| ~3938 (unsafe after safe) | goto out | YES | YES | ✅ | |
| ~3952 (safe + GOT_UNSAFE) | goto out after __unregister_request | YES | YES (__unregister_request put + out put) | ✅ | __unregister_request() drops unsafe reference; out put drops lookup reference → balanced |
| Normal path (everything else, through out_err) | reaches end (fall through to out) | YES | YES (out put at ~4103) | ⚠️ depends on complete_request | **complete_request(mdsc, req)** is called at ~4098, before final put. If complete_request internally calls ceph_mdsc_put_request(), the out put becomes an excess put (refcount already zero). That matches the warning at line 4103. |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
One-line reasoning: On the normal (non-skip) path, `complete_request()` likely calls `ceph_mdsc_put_request()` before the final `ceph_mdsc_put_request(req)` at `out:`, causing a double release and an excess put at line 4103.
```
