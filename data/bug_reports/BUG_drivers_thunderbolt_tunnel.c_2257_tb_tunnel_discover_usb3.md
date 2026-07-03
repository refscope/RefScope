# REAL BUG: drivers/thunderbolt/tunnel.c:2257 tb_tunnel_discover_usb3()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| Bandwidth read failure → `err_deactivate` | NULL | YES | same as above | ❓ | same double-put risk |

## Full Response

```
| Path | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| Early return (port not enabled) | NULL | NO (before alloc) | N/A | ✅ | No tunnel allocated |
| Alloc failed (`!tunnel`) | NULL | NO (alloc returned NULL) | N/A | ✅ | No ref held |
| Success (`return tunnel`) | tunnel ptr | YES (ref=1) | NO | ✅ | Caller will own and eventually put |
| First path discovery failure → `err_free` | NULL | YES | YES (`tb_tunnel_put`) | ✅ | Single put releases initial ref |
| Second path discovery failure → `err_deactivate` | NULL | YES | YES (`tb_tunnel_put`) + possibly `tb_tunnel_put` inside `tb_tunnel_deactivate` | ❓ | **Double put if deactivate already puts** |
| Validation failures (dst_port, src_port, not enabled) → `err_deactivate` | NULL | YES | same as above | ❓ | same double-put risk |
| Bandwidth read failure → `err_deactivate` | NULL | YES | same as above | ❓ | same double-put risk |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On all error paths that go through `err_deactivate`, `tb_tunnel_deactivate()` is called before `tb_tunnel_put()`. The excess put warning at line 2257 indicates that the refcount is already zero when `tb_tunnel_put()` executes, meaning `tb_tunnel_deactivate()` internally called `tb_tunnel_put()` (or released the kref), leading to a double put and use-after-free. Without that internal put, the warning would not trigger.
```
