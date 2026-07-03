# REAL BUG: drivers/net/ethernet/mellanox/mlx4/en_rx.c:1130 mlx4_en_config_rss_qp()

**Confidence**: HIGH | **Counter**: `$->refcount.refs.counter`

## Reasoning

- **Unconditional GET?** Yes — `mlx4_qp_alloc` always sets refcount to 1 → every path after it must not over‑release.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1095 | return -ENOMEM | NO (before alloc) | N/A | ✅ | context allocation failed |
| L1098 | goto out after alloc fail | NO (alloc returned error) | NO | ✅ | mlx4_qp_alloc error → no qp acquired |
| L1119‑L1121 (success) | return 0 | YES (unconditional from L1094) | NO | ✅ | qp handed to caller – caller will put later |
| L1115‑L1118 (error path) | goto out → return err | YES | ❌ excess put | ❌ LEAK/OVERPUT | mlx4_qp_remove likely already drops ref, then mlx4_qp_free at L1130 does another put → **excess put** |

- **GET**: `mlx4_qp_alloc` is unconditional (contract: unconditional, refcount_set). After it succeeds, refcount = 1.
- On the error path (`mlx4_qp_to_ready` fails), the code calls:
  1. `mlx4_qp_remove(mdev->dev, qp)`   ← **likely does a kref_put**, dropping refcount to 0
  2. `mlx4_qp_free(mdev->dev, qp)`     ← **calls mlx4_put_qp (another kref_put) → excess put** at L1130

The warning explicitly flags a “refcount excess put” on L1130, confirming that `mlx4_qp_remove` has already consumed the last reference before `mlx4_qp_free` runs.

## Pre‑Verdict Checklist

- **Ownership transferred?** No — on the error path we still own the reference; the double put indicates both `mlx4_qp_remove` and `mlx4_qp_free` act as release functions.
- **goto blind spots?** Not relevant here; the error path includes explicit puts that overflow.
- **Probe/device‑lifetime?** Not applicable.
- **Unconditional GET?** Yes — `mlx4_qp_alloc` always sets refcount to 1 → every path after it must not over‑release.

```
VERDICT: REAL_BUG
CONFIDENCE: HIGH
```
`mlx4_qp_remove` already releases the QP reference; subsequent `mlx4_qp_free` at L1130 causes a refcount underflow (excess put).
```
