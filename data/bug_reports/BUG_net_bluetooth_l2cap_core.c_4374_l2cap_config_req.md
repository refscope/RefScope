# REAL BUG: net/bluetooth/l2cap_core.c:4374 l2cap_config_req()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| L4361 | return err (via all other goto unlock) | YES | YES (unlock label put) | ✅ | normal success or other paths without early PUT |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L4274 | return -EPROTO | NO (before get) | N/A | ✅ | early cmd_len check, no ref |
| L4282 | return 0       | NO (get failed, chan=NULL) | N/A | ✅ | l2cap_get_chan_by_scid returned NULL |
| L4289 | goto unlock    | YES | YES (unlock label put) | ✅ | state check fails, cmd_reject, no extra put |
| L4298 | goto unlock    | YES | YES (unlock label put) | ✅ | conf buffer too small, l2cap_send_cmd only |
| L4309 | goto unlock    | YES | YES (unlock label put) | ✅ | CONTINUATION flag, send empty rsp, no extra put |
| L4315 | goto unlock    | YES | **YES (disconn_req PUT) + unlock PUT** | ❌ EXCESS PUT | len<0 branch: l2cap_send_disconn_req (PUT) then goto unlock → extra put at L4374 |
| L4356 | goto unlock (via err<0) | YES | **YES (disconn_req PUT) + unlock PUT** | ❌ EXCESS PUT | err<0 inside CONFIG_INPUT_DONE block: l2cap_send_disconn_req (PUT) then goto unlock → extra put |
| L4356 | goto unlock (via err>=0) | YES | **YES (chan_ready PUT) + unlock PUT** | ⚠️ LIKELY EXCESS PUT | l2cap_chan_ready also marked as PUT; double-put possible if it drops the same kref |
| L4347 | goto unlock    | YES | YES (unlock label put) | ✅ | CONF_OUTPUT_DONE not set, no extra put |
| L4361 | return err (via all other goto unlock) | YES | YES (unlock label put) | ✅ | normal success or other paths without early PUT |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
l2cap_send_disconn_req is a PUT function that drops the channel's kref. On the len<0 error path (L4315) and on the err<0 path inside the CONFIG_INPUT_DONE block (L4356), the function calls l2cap_send_disconn_req before falling through to the common unlock label, which unconditionally does l2cap_chan_put, leading to a double put (refcount underflow). The `l2cap_chan_ready` path may also double-put, but is not needed to confirm the bug.
```
