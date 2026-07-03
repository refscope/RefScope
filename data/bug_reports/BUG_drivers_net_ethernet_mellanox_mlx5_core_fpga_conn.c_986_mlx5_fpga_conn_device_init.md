# REAL BUG: drivers/net/ethernet/mellanox/mlx5/core/fpga/conn.c:986 mlx5_fpga_conn_device_init()

**Confidence**: HIGH | **Counter**: `fdev->conn_res.uar->ref_count.refcount.refs.counter`

## Reasoning

unconditional GET with `→kref_get(get),kref_get(get)` – it acquires **two** references on the same `refcount`. `mlx5_put_uars_page` releases only **one** reference. Every path that successfully obtains the uar page calls `mlx5_put_uars_page` at most once, leaving one reference permanently leaked.

## Full Response

```
| Line | Return Type           | GET Done?          | PUT Done?          | Balanced? | Notes |
|------|-----------------------|--------------------|--------------------|-----------|-------|
| L950 | error (goto out)      | NO (before get)    | N/A                | ✅        | RoCE enable failed, no uar page acquired |
| L961 | error (goto err_roce) | NO (IS_ERR)        | N/A                | ✅        | get_uars_page failed, no ref held |
| L968 | error (goto err_uar)  | YES (2 krefs)      | YES (1 kref via mlx5_put_uars_page) | ❌ LEAK   | err_uar calls mlx5_put_uars_page once, leaving one extra ref |
| L978 | error (goto err_dealloc_pd) | YES (2 krefs) | YES (1 kref via fallthrough to err_uar) | ❌ LEAK   | same, only one put |
| L980 | success (return 0)    | YES (2 krefs)      | NO                 | ❌ LEAK   | reference held for device lifetime; cleanup will likely put only once → one ref leaked |

⚠️ `mlx5_get_uars_page` contract states unconditional GET with `→kref_get(get),kref_get(get)` – it acquires **two** references on the same `refcount`. `mlx5_put_uars_page` releases only **one** reference. Every path that successfully obtains the uar page calls `mlx5_put_uars_page` at most once, leaving one reference permanently leaked.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`mlx5_get_uars_page` takes two kref references but the caller only releases one on error paths and none on success, causing an unmatched extra reference in every case.
```
