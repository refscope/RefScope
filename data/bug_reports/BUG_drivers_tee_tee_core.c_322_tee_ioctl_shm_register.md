# REAL BUG: drivers/tee/tee_core.c:322 tee_ioctl_shm_register()

**Confidence**: HIGH | **Counter**: `$->refcount.refs.counter`

## Reasoning

, get_fd failure) → L316 | error (ret < 0) then put       | YES (register only; get_fd may NOT have done a get) | YES (get_fd internal tee_shm_put) + YES (caller tee_shm_put) | ❌ **IMBALANCE** | Contract: tee_shm_get_fd may do tee_shm_put on failure without a prior get → double put on this path. |

## Full Response

```
```
| Line                | Return Type                       | GET Done?                           | PUT Done?                            | Balanced? | Notes                                                                                                         |
|---------------------|-----------------------------------|-------------------------------------|--------------------------------------|-----------|---------------------------------------------------------------------------------------------------------------|
| ~L296               | error (copy_from_user)            | NO (shm not yet allocated)          | N/A                                  | ✅        |                                                                                                               |
| ~L302               | error (flags)                     | NO                                  | N/A                                  | ✅        |                                                                                                               |
| ~L305               | error (IS_ERR)                    | NO (shm is ERR_PTR)                 | N/A                                  | ✅        |                                                                                                               |
| ~L311 (copy_to_user fail) → L316 | error (ret = -EFAULT) then put | YES (tee_shm_register_user_buf)     | YES (caller tee_shm_put)             | ✅        | Caller owns one get, releases it correctly.                                                                    |
| ~L311 (copy_to_user ok, get_fd success) → L316 | success (ret = fd ≥ 0) then put | YES + YES (register + get_fd internal get) | YES (caller put)                  | ✅        | get_fd takes extra ref for fd; caller drops its initial ref; fd holds remaining ref.                           |
| ~L311 (copy_to_user ok, get_fd failure) → L316 | error (ret < 0) then put       | YES (register only; get_fd may NOT have done a get) | YES (get_fd internal tee_shm_put) + YES (caller tee_shm_put) | ❌ **IMBALANCE** | Contract: tee_shm_get_fd may do tee_shm_put on failure without a prior get → double put on this path. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The contract states tee_shm_get_fd() can perform a tee_shm_put on some (error) path, yet the caller always calls tee_shm_put after it, causing an extra put when get_fd already released the reference.
```
```
