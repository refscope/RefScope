# REAL BUG: drivers/of/irq.c:412 of_irq_parse_raw()

**Confidence**: HIGH | **Counter**: `ipar->kobj.kref.refcount.refs.counter`

## Reasoning

| L408   | error via fail    | YES (ipar held, may be NULL) | YES (fail does of_node_put)     | ✅        | while loop ends, ipar becomes NULL or an error path                                               |

## Full Response

```
```
| Line   | Return Type       | GET Done?                | PUT Done?                       | Balanced? | Notes                                                                                             |
|--------|-------------------|--------------------------|---------------------------------|-----------|---------------------------------------------------------------------------------------------------|
| L272   | error via fail    | YES (ipar held)          | YES (fail does of_node_put)     | ✅        | ipar is NULL, put is no‑op                                                                        |
| L281   | error via fail    | YES (ipar held)          | YES (fail does of_node_put)     | ✅        | args_count mismatch                                                                               |
| L309   | error via fail    | YES (ipar held)          | YES (fail does of_node_put)     | ✅        | addrsize overflow warning                                                                         |
| L318   | **early success** | **YES (ipar held)**      | **NO**                          | ❌ LEAK   | `return 0` inside loop when intc && no map – ipar not released                                    |
| L329   | error via fail    | YES (ipar held)          | YES (fail does of_node_put)     | ✅        | addrsize && !addr                                                                                 |
| L348   | goto skiplevel    | YES (ipar held)          | YES (skiplevel does of_node_put then takes newpar) | ✅ | no map, finds parent                                                                              |
| L360   | error via fail    | YES (ipar held)          | YES (fail does of_node_put)     | ✅        | of_irq_parse_imap_parent returned NULL                                                           |
| L370   | error via fail    | YES (ipar held)          | YES (fail does of_node_put)     | ✅        | no match in interrupt-map entries                                                                |
| L400   | self‑map success  | YES (ipar + new ref)     | YES (of_node_put(ipar) before return) | ✅        | leaves the reference from of_irq_parse_imap_parent in out_irq->np for the caller                  |
| L408   | error via fail    | YES (ipar held, may be NULL) | YES (fail does of_node_put)     | ✅        | while loop ends, ipar becomes NULL or an error path                                               |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
```
```
