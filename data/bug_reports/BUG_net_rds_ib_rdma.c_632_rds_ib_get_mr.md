# REAL BUG: net/rds/ib_rdma.c:632 rds_ib_get_mr()

**Confidence**: HIGH | **Counter**: `$->refcount.refs.counter`

## Reasoning

| L617→L626 (IS_ERR fallthrough) | error | YES   | YES (out) | ✅         | error path reaches `out:` → put |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L598 (ODP success) | return ibmr  | YES       | NO        | ❌ LEAK    | direct return, no rds_ib_dev_put |
| L619 (non-ODP success) | return ibmr | YES       | NO        | ❌ LEAK    | direct return, no rds_ib_dev_put |
| L556 (goto out, rds_ibdev NULL) | error | NO        | - (no ref) | ✅         | get failed → no ref to release |
| L567 (goto out) | error     | YES       | YES (out) | ✅         | goto out → put |
| L577 (goto out) | error     | YES       | YES (out) | ✅         | goto out → put |
| L586 (goto out) | error     | YES       | YES (out) | ✅         | goto out → put |
| L605 (goto out) | error     | YES       | YES (out) | ✅         | goto out → put |
| L611 (goto out) | error     | YES       | YES (out) | ✅         | goto out → put |
| L617→L626 (IS_ERR fallthrough) | error | YES   | YES (out) | ✅         | error path reaches `out:` → put |
```

VERDICT: REAL_BUG
CONFIDENCE: HIGH

`rds_ib_get_device` acquires a reference on `rds_ibdev`. All error paths reach `out:` and release it, but the two success paths (L598 ODP and L619 non‑ODP) return `ibmr` directly without calling `rds_ib_dev_put`. No ownership transfer to the returned object is shown, causing a refcount leak on every successful allocation.
```
