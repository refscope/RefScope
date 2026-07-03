# REAL BUG: fs/ntfs/super.c:2557 ntfs_fill_super()

**Confidence**: HIGH | **Counter**: `$->i_count.counter`

## Reasoning

| Root `d_make_root` success (L1558) | `return 0` | YES (consumed) | Effective put via `d_make_root` | ✅ | |

## Full Response

```
## Path Table

| Line (approx) | Return Type | GET Done? (root inode) | PUT Done? | Balanced? | Notes |
|---------------|-------------|------------------------|-----------|-----------|-------|
| Early returns (L1248–L1254) | `return -EINVAL` / `-ENOMEM` | NO (before any inode get) | N/A | ✅ | |
| After `ntfs_init_from_boot` err (L1283) | `goto out` | NO | N/A | ✅ | |
| `$Volume` IS_ERR (L1288) | `goto out` | NO (get failed) | N/A | ✅ | |
| `$Volume` attr validation fail (L1316) | `goto put_inode_out` | YES (Volume) | YES (`iput(inode)` at label) | ✅ | |
| `$MFTMirr` IS_ERR (L1340) | `goto out` | NO (get failed) | N/A | ✅ | |
| `$LogFile` IS_ERR (L1356) | `goto out` | NO (get failed) | N/A | ✅ | |
| `$LogFile` replay error (L1362) | `goto put_inode_out` | YES (LogFile) | YES (`iput(inode)`) | ✅ | |
| `$MFT` IS_ERR (L1383) | `goto out` | NO (get failed) | N/A | ✅ | |
| `$MFT` subrecords/bitmap/wnd_init errors (L1399–L1419) | `goto put_inode_out` | YES ($MFT) | YES (`iput(inode)`) | ✅ | |
| `$Bitmap` IS_ERR (L1427) | `goto out` | NO (get failed) | N/A | ✅ | |
| `$Bitmap` size/wnd_init errors (L1434–L1442) | `goto put_inode_out` | YES ($Bitmap) | YES (`iput(inode)`) | ✅ | |
| `$BadClus` IS_ERR (L1454) | `goto out` | NO (get failed) | N/A | ✅ | |
| `$AttrDef` IS_ERR (L1473) | `goto out` | NO (get failed) | N/A | ✅ | |
| `$AttrDef` size/read/type errors (L1481–L1491) | `goto put_inode_out` | YES ($AttrDef) | YES (`iput(inode)`) | ✅ | |
| `$UpCase` IS_ERR (L1503) | `goto out` | NO (get failed) | N/A | ✅ | |
| `$UpCase` size/read errors (L1508–L1513) | `goto put_inode_out` | YES ($UpCase) | YES (`iput(inode)`) | ✅ | |
| NTFS3 specific init errors (L1526–L1540) | `goto load_root` / `goto out` | NO (before root get) | N/A | ✅ | |
| **Root** `ntfs_iget5` IS_ERR (L1546) | `goto out` | NO (get failed) | N/A | ✅ | |
| Root `!inode->i_op` (L1554) | `goto put_inode_out` | YES (root) | YES (`iput(inode)`) | ✅ | |
| **Root** `d_make_root` fails (L1557) | `goto out` | YES (root) | NO (skips `put_inode_out`, no iput in `out`) | ❌ **LEAK** | `inode` ref held, not released |
| Root `d_make_root` success (L1558) | `return 0` | YES (consumed) | Effective put via `d_make_root` | ✅ | |

---

## VERDICT: REAL_BUG  
## CONFIDENCE: HIGH  

Missing `iput(inode)` on the error path when `d_make_root()` returns `NULL` (line ~L1557), causing a leak of the root inode reference acquired by `ntfs_iget5()`.
```
