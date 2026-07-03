# REAL BUG: drivers/firmware/arm_scmi/driver.c:2808 scmi_txrx_setup()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

calls took references                                          | YES       | ✅        | References stored in `info` will be released by later `scmi_chan_cleanup`/device removal                       |

## Full Response

```
| Line   | Return Type                           | GET Done?                                                                 | PUT Done? | Balanced? | Notes                                                                                                           |
|--------|---------------------------------------|---------------------------------------------------------------------------|-----------|-----------|-----------------------------------------------------------------------------------------------------------------|
| L2808  | error (first call fails)             | YES — scmi_chan_setup acquires kref on device/channel before failing      | NO        | ❌ LEAK   | No kref_put in error path; ref taken by first scmi_chan_setup is leaked                                       |
| L2808  | error (second call returns -ENOMEM)  | YES — second scmi_chan_setup acquires kref on its channel’s device, fails  | NO        | ❌ LEAK   | No cleanup for second channel’s reference on -ENOMEM; first channel ref is stored but second is dropped         |
| L2808  | success (ret == 0)                   | YES — both calls took references                                          | YES       | ✅        | References stored in `info` will be released by later `scmi_chan_cleanup`/device removal                       |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`scmi_chan_setup()` acquires a kref on a device-kobj during channel setup; the caller `scmi_txrx_setup()` immediately returns the error code without releasing that reference, leading to a refcount leak on any failure path.
```
