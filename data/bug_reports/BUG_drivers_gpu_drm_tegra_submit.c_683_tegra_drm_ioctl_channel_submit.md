# REAL BUG: drivers/gpu/drm/tegra/submit.c:683 tegra_drm_ioctl_channel_submit()

**Confidence**: HIGH | **Counter**: `$->ref.refs.counter`

## Reasoning

| goto put_job          | YES       | NO                 | ❌ LEAK   | Success path; same issue as L642.                                                                                                                                                                                                  |

## Full Response

```
| Line | Return Type           | GET Done? | PUT Done?          | Balanced? | Notes                                                                                                                                                                                                                              |
|------|-----------------------|-----------|--------------------|-----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| L528 | return -EINVAL        | NO        | N/A                | ✅        | No get yet                                                                                                                                                                                                                         |
| L537 | goto unlock           | NO        | N/A                | ✅        |                                                                                                                                                                                                                                    |
| L544 | goto unlock           | NO        | N/A                | ✅        |                                                                                                                                                                                                                                    |
| L553 | goto unlock           | NO        | N/A                | ✅        |                                                                                                                                                                                                                                    |
| L560 | goto unlock           | NO        | N/A                | ✅        |                                                                                                                                                                                                                                    |
| L566 | goto put_bo           | NO        | N/A                | ✅        |                                                                                                                                                                                                                                    |
| L572 | goto free_job_data    | NO        | N/A                | ✅        |                                                                                                                                                                                                                                    |
| L578 | goto free_job_data    | NO        | N/A                | ✅        |                                                                                                                                                                        
```
