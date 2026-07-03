# REAL BUG: net/packet/af_packet.c:4242 packet_notifier()

**Confidence**: MEDIUM | **Counter**: `$->sk_refcnt.refs.counter`

## Reasoning

- The single return point of `packet_notifier` (line 4241) does not itself perform any refcount operation; the excess put occurs earlier when `__unregister_prot_hook` runs inside the loop. The warning line 4242 likely marks the function exit where the unbalanced put is detected by the checker.

## Full Response

```
[NEED_SOURCE] register_prot_hook
[NEED_SOURCE] __unregister_prot_hook

## Path Table

The function `packet_notifier` has a single return at line 4241 (return NOTIFY_DONE). However, the refcount warning concerns `__unregister_prot_hook` called inside the loop, not the function’s own return. Below I enumerate the execution paths that reach the `__unregister_prot_hook` call and evaluate the get/put balance.

| Line(s) | Scenario / Path                                                       | GET Done? (`sock_hold` via `register_prot_hook`) | PUT Done? (`sock_put` via `__unregister_prot_hook`) | Balanced? | Notes |
|---------|-----------------------------------------------------------------------|--------------------------------------------------|-----------------------------------------------------|-----------|-------|
| L4207-4208 | NETDEV_DOWN or NETDEV_UNREGISTER, `dev->ifindex == po->ifindex` and `PACKET_SOCK_RUNNING` set | **Unknown** – depends on whether `register_prot_hook` took a reference when it set the flag | **YES** (unconditional, per contract) | ❓ POSSIBLE EXCESS PUT | The flag is assumed to indicate a held reference, but if `register_prot_hook` can set the flag without successfully incrementing `sk->sk_refcnt`, this path releases a reference that was never held → excess put. |
| L4226-4227 | NETDEV_UP, `dev->ifindex == po->ifindex`, `po->num != 0`             | **YES** (if `register_prot_hook` takes a reference on success) | N/A                                                | — | Later unregister will release it. |
| L4205-4221 | Same DOWN/UNREGISTER path as above, but flag not set                 | N/A                                              | NO                                                  | ✅ | No operation. |
| L4205-4221 | DOWN/UNREGISTER, `dev->ifindex != po->ifindex`                       | N/A                                              | NO                                                  | ✅ | No operation. |

## Reasoning

- **`__unregister_prot_hook`** unconditionally calls `__sock_put` (contract). It must be paired with a prior `sock_hold`.
- The notifier guards this put with `PACKET_SOCK_RUNNING`. That flag is presumably set by `register_prot_hook` when a protocol hook is installed.
- If `register_prot_hook` can set the flag **before** taking the socket reference, and then fail (e.g., error after flag set), the flag remains set but no reference exists. A later DOWN/UNREGISTER would then call `__unregister_prot_hook`, releasing a nonexistent reference → **excess put**.
- Because the source of `register_prot_hook` is not provided, I cannot confirm the exact ordering. However, the smatch warning explicitly reports an excess put on `sk->sk_refcnt`, which strongly indicates an imbalance.
- The single return point of `packet_notifier` (line 4241) does not itself perform any refcount operation; the excess put occurs earlier when `__unregister_prot_hook` runs inside the loop. The warning line 4242 likely marks the func
```
