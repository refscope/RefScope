# REAL BUG: drivers/accel/ivpu/ivpu_drv.c:431 ivpu_wait_for_ready()

**Confidence**: MEDIUM | **Counter**: `$->ipc->rx_msg_count.counter`

## Reasoning

PUT always does (or when the PUT is unconditional and the GET is conditional), the imbalance is real.

## Full Response

```
[NEED_SOURCE] ivpu_ipc_irq_handler  
[NEED_SOURCE] ivpu_ipc_receive

## Path Table — `ivpu_wait_for_ready()` (drivers/accel/ivpu/ivpu_drv.c)

The function performs no direct refcount operations on `rx_msg_count`; all GET/PUT activity is hidden inside
`ivpu_ipc_irq_handler()` and `ivpu_ipc_receive()`. The warning is about an **excess put** (i.e., decrement on an
already‑zero counter) observed at line 431, which the path analysis must explain.

### Assumptions (based on naming patterns and the “excess put” warning)

- **GET** `ivpu_ipc_irq_handler()` – likely increments `rx_msg_count` when a pending IRQ contains a message.
- **PUT** `ivpu_ipc_receive()` – likely decrements `rx_msg_count` when it consumes a message; the warning suggests it may
  decrement **unconditionally** (even on `-ETIMEDOUT`), or the irq handler sometimes leaves the counter unchanged.
- These contracts are **unconfirmed** – hence the `[NEED_SOURCE]` requests.

The loop structure is:

```c
while (1) {
    ivpu_ipc_irq_handler(vdev);               // possible GET
    ret = ivpu_ipc_receive(vdev, &cons, ...); // possible PUT
    if (ret != -ETIMEDOUT || timeout)
        break;
    cond_resched();
}
```

So **each iteration** executes one GET and one PUT, but the “GET” may actually be a no‑op if no IRQ is pending,
while the “PUT” may always fire. This yields the following return‑path analysis.

| Line  | Return Type         | GETs Executed       | PUTs Executed       | Balanced? | Notes                                                                                      |
|-------|---------------------|---------------------|---------------------|-----------|--------------------------------------------------------------------------------------------|
| L405  | early return 0      | 0                   | 0                   | ✅         | No loop entered; refcount untouched.                                                       |
| L423  | return -EIO         | N × irq_handler     | N × ipc_receive     | ❌         | If irq_handler skips increment while receive always decrements, an **excess put** occurs.  |
| L429  | return ret (0/non0) | N × irq_handler     | N × ipc_receive     | ❌         | Same imbalance; the reported “excess put” manifests on this final return path.             |

- **L423 / L429**: The number of iterations `N` is ≥ 1 and depends on timeout / message arrival.
  The warning at line 431 is the static checker detecting that `ivpu_ipc_receive()` can decrement
  `rx_msg_count.counter` after `ivpu_ipc_irq_handler()` has **not** performed a corresponding increment,
  leading to a refcount underflow. This is the classic pattern of a missing conditional guard on the
  PUT side or an unconditionally‑decremented PUT paired with a conditional GET.

## Pre‑Verdict Checklist

1. **“Held for device lifetime”?** – Not applicable; no such claim exists for the rx counter.  
2. **“Ownership transferred”?** – Not applicable; the counter is a per‑IPC message reference, not transferre
```
