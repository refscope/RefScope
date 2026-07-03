# REAL BUG: drivers/thunderbolt/icm.c:1009 icm_fr_xdomain_connected()

**Confidence**: HIGH | **Counter**: `xd->dev.kobj.kref.refcount.refs.counter`

## Reasoning

at is the case, the subsequent explicit `tb_xdomain_put` in the caller becomes a **double put**, exactly matching the observed “refcount excess put” on the device’s kref. The fact that the warning is an *excess* put, not a leak, strongly supports that `remove_xdomain` already releases a reference.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L942 | early return (invalid params) | NO (before get) | N/A | ✅ | No xd get possible |
| L954 | `return` after update+put | YES (via `tb_xdomain_find_by_uuid` at L947) | YES (`tb_xdomain_put(xd)` at L954) | ✅ | Clean match‑and‑release path |
| L958 (after mismatch) | continues (no immediate return) | YES (same get as above) | YES? (`remove_xdomain(xd)` then `tb_xdomain_put(xd)`) | ⚠️ **DOUBLE PUT** if `remove_xdomain` internally calls `tb_xdomain_put` | Both the find‑by‑uuid get and the later explicit put may be released, but `remove_xdomain` may already consume a reference |
| L970 (find‑by‑link‑depth) | continues | YES (via `tb_xdomain_find_by_link_depth`) | YES? (`remove_xdomain(xd)` then `tb_xdomain_put(xd)`) | ⚠️ **Same risk** | Second get path also pairs removal with an explicit put |
| L982 | `return` (no switch) | No new get; all earlier xd gets already put (see above) | Already handled | ✅ (assuming no double put above) | Only xd references from earlier blocks are already released |
| L987 | end‑of‑function (implicit) | No new get | Already handled | ✅ | No lingering xd reference |

`remove_xdomain` (unknown PUT contract) is the critical callee. [NEED_SOURCE] remove_xdomain

In typical kernel device–list patterns, `remove_xdomain` performs a `list_del_init` *and* a `tb_xdomain_put` to drop the list’s reference. If that is the case, the subsequent explicit `tb_xdomain_put` in the caller becomes a **double put**, exactly matching the observed “refcount excess put” on the device’s kref. The fact that the warning is an *excess* put, not a leak, strongly supports that `remove_xdomain` already releases a reference.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`remove_xdomain` likely calls `tb_xdomain_put` internally; both the match‑and‑remove path (L958) and the link‑depth lookup path (L970) therefore perform an extra put on the already‑released xdomain reference.
```
