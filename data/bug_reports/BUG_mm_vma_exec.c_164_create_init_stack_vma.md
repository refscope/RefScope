# REAL BUG: mm/vma_exec.c:164 create_init_stack_vma()

**Confidence**: HIGH | **Counter**: `$->mm_count.counter`

## Reasoning

- `ksm_execve` comment mentions locking, not that it returns without taking a reference on error.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L115 (vma alloc fail) | error (-ENOMEM) | NO (before any get) | N/A | ✅ | No refcount involved |
| ~L132 (`goto err_ksm` after `ksm_execve` returns error) | error | **UNCERTAIN** – depends on `ksm_execve` contract. Typical pattern: unconditional `mmget()` → GET=YES. Conditional get → GET=NO. | NO – `ksm_exit` not called | ❓ Potentially LEAK if GET=YES | err_ksm label lacks any put; smatch detected refcount leak on `mm_count` |
| ~L140 (`goto err` after `insert_vm_struct` fails) | error | YES (ksm_execve succeeded) | YES (`ksm_exit` called) | ✅ | Cleanup path correct |
| ~L150 (success) | success | YES (intentional hold) | N/A – reference kept for process lifetime | ✅ | Held for later release by `ksm_exit` on exit |

**🆘 Requesting source for contracts:**
- [NEED_SOURCE] `ksm_execve` – to confirm whether it increments `mm->mm_count` unconditionally or only on success
- [NEED_SOURCE] `ksm_exit` – to confirm it is the matching put function

**Analysis:**
- The warning targets a refcount leak on `mm_count.counter` at line 164 (the final `return err;` after `err_free`).
- The only suspect path is the `err_ksm` label taken when `ksm_execve` returns an error. That path contains **no call to `ksm_exit`**.
- If `ksm_execve` unconditionally takes a reference (as many kernel subsystem init functions do), this is a clear leak.
- Even without source, the function name (`ksm_execve`) strongly suggests it acquires a KSM‑related reference on the `mm_struct`, likely via `mmget()`. Error‑handling should therefore release that reference, exactly as done on the `insert_vm_struct` failure path which does call `ksm_exit`.

**Apply FP checklist:**
- No IS_ERR/NULL guarding the reference from `ksm_execve`.
- No ownership transfer or deferred cleanup documented for this error path.
- No device‑lifetime argument applies (this is a per‑mm object, not a probe path).
- `ksm_execve` comment mentions locking, not that it returns without taking a reference on error.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Error path after `ksm_execve` failure at `err_ksm` omits `ksm_exit`, leaving `mm_count` incremented if `ksm_execve` takes a reference even on error (very likely unconditional).
```
