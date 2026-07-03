# REAL BUG: fs/smb/client/file.c:543 cifs_posix_open()

**Confidence**: MEDIUM | **Counter**: `$->tl_count.counter`

## Reasoning

ct marks `cifs_sb_tlink()` as **conditional_on_path**, meaning the refcount increment may **not** happen even when a non-ERR pointer is returned. On those paths the subsequent unconditional `cifs_put_tlink(tlink)` would be an **excess put**, dropping the counter below zero.

## Full Response

```
| Line | Return Type          | GET Done?                      | PUT Done? | Balanced? | Notes                                                                 |
|------|----------------------|--------------------------------|-----------|-----------|-----------------------------------------------------------------------|
| L498 | return -ENOMEM       | NO (before call)               | N/A       | ✅        | presp_data allocation failed, no tlink involved                       |
| L503 | goto posix_open_ret  | NO (IS_ERR, get failed)        | N/A       | ✅        | Error path from cifs_sb_tlink, no ref taken                           |
| L516 | goto posix_open_ret  | ❓ (valid tlink, but GET may be conditional) | YES       | ❓        | After L510 create, put unconditionally at L513; if GET didn’t bump ref, excess put |
| L519 | goto posix_open_ret  | ❓                             | YES       | ❓        | Same, put already executed at L513                                    |
| L522 | goto posix_open_ret  | ❓                             | YES       | ❓        | Same                                                                  |
| L532 | goto posix_open_ret  | ❓                             | YES       | ❓        | Same                                                                  |
| L541 | return rc (falls thru)| ❓                             | YES       | ❓        | Same, after else block, reaches end with put already done             |

✅ = Balanced only if cifs_sb_tlink unconditionally takes a reference on success.  
❓ = The contract marks `cifs_sb_tlink()` as **conditional_on_path**, meaning the refcount increment may **not** happen even when a non-ERR pointer is returned. On those paths the subsequent unconditional `cifs_put_tlink(tlink)` would be an **excess put**, dropping the counter below zero.

---
### Analysis

**PRE-VERDICT CHECKLIST**

1. **“Held for device lifetime”?** No – the tlink is obtained and released within the same function; not a probe/remove pattern.
2. **“Ownership transferred”?** No – the tlink is not stored in any long-lived structure that would later release it; all cleanup is local.
3. **Unconditional GET?** According to the contract the get is **conditional** (`conditional_on_path`). Thus a successful call (IS_ERR false) does **not** guarantee that `$->tl_count` was incremented.
4. **`goto out` between GET and PUT?** All paths after `cifs_put_tlink(tlink)` at L513 go directly to `posix_open_ret`, where **no put** is performed. So if the GET happened, the single put is correct; if the GET was skipped, the put is excess.

The core problem: the contract explicitly states that the GET is conditional. In this function the put is executed unconditionally for every path where the tlink was not an error pointer. Therefore smatch’s warning of an **excess put** on `tl_count.counter` is consistent – a put that is not preceded by a corresponding get.

Because the source of `cifs_sb_tlink()` is not provided and the exact cond
```
