# REAL BUG: drivers/infiniband/sw/siw/siw_cm.c:1949 siw_create_listen()

**Confidence**: HIGH | **Counter**: `$->dev_refcnt.refs.counter`

## Reasoning

| L1916 | success (return 0) | ndev may be NULL or not | YES (dev_put(ndev) at L1945) | ❌ if ndev=NULL | same bug on success path |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1811 | error (EAFNOSUPPORT) | NO | NO | ✅ | ndev=NULL, early return |
| L1815 | error (sock_create fail) | NO | NO | ✅ | ndev=NULL, early return |
| L1849 | error (ip6_sock_set_v6only fail → goto error) | NO | YES (dev_put(NULL) at L1949) | ❌ | ndev=NULL before get |
| L1838 | error (ib_device_get_netdev NULL, AF_INET → goto error) | NO | YES (dev_put(NULL)) | ❌ | ndev=NULL, get failed |
| L1864 | error (bind fail, AF_INET wildcard false, ndev=NULL) | NO | YES | ❌ | ndev=NULL |
| L1864 | error (bind fail, AF_INET wildcard true, ndev!=NULL) | YES | YES | ✅ | one get, one put |
| L1855 | error (ib_device_get_netdev NULL, AF_INET6 → goto error) | NO | YES | ❌ | ndev=NULL |
| L1864 | error (bind fail, AF_INET6 wildcard false, ndev=NULL) | NO | YES | ❌ | |
| L1864 | error (bind fail, AF_INET6 wildcard true, ndev!=NULL) | YES | YES | ✅ | |
| L1873 | error (cep alloc fail, ndev may be NULL or not) | depends on wildcard | YES (unconditional) | ❌ if ndev=NULL | bug when ndev=NULL |
| L1882 | error (alloc_work fail) | similar | YES | ❌ if ndev=NULL | |
| L1888 | error (listen fail) | similar | YES | ❌ if ndev=NULL | |
| L1902 | error (provider_data kmalloc fail) | similar | YES | ❌ if ndev=NULL | |
| L1916 | success (return 0) | ndev may be NULL or not | YES (dev_put(ndev) at L1945) | ❌ if ndev=NULL | same bug on success path |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`dev_put(ndev)` is called unconditionally in both the error label (L1949) and the success path (L1945) without checking whether `ndev` was obtained. On paths where the wildcard condition is false or an error occurs before `ib_device_get_netdev`, `ndev` remains NULL, causing a `dev_put(NULL)` which violates the contract (no NULL check) and results in a refcount imbalance (excess put).
```
