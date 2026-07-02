import json
import os
from collections import defaultdict


PAIR_CANDIDATE_FILENAME = "function_pair_candidates.json"

# Metadata files produced by the pipeline — not per-function analysis results
_METADATA_FILES = {
    "refcount_callgraph.json",
    "wrapper_stage_traces.json",
    "function_pair_candidates.json",
    "confirmed_bug_candidates_input.json",
}


def _strip_struct_keywords(type_chain):
    """Remove C keywords (struct/enum/union) from type-chain parts."""
    if not type_chain:
        return type_chain
    parts = type_chain.split("--")
    cleaned = []
    for p in parts:
        p = p.strip()
        for kw in ("struct ", "enum ", "union "):
            if p.startswith(kw):
                p = p[len(kw):]
        cleaned.append(p)
    return "--".join(cleaned)


def _normalize_functionality_entry(entry):
    """Convert a raw functionality_list entry to the canonical critical-variable dict."""
    if len(entry) < 5:
        return None
    location = "parameter" if entry[1] == "para" else entry[1]
    return {
        "direction": entry[0],
        "location": location,
        "index": entry[2],
        "member_access_path": entry[3],
        "member_type_chain": _strip_struct_keywords(entry[4]),
    }


def _dict_to_tuple(d):
    return tuple(sorted(d.items()))


def _tuple_to_dict(t):
    return dict(t)


def collect_critical_variables(function_result_dir):
    """
    Scan per-function JSON files and collect critical variables by direction.
    Returns (get_map, put_map, set_map) where each is {function_name: [cv_dict, ...]}.
    """
    get_map = defaultdict(list)
    put_map = defaultdict(list)
    set_map = defaultdict(list)

    for filename in os.listdir(function_result_dir):
        if not filename.endswith(".json"):
            continue
        if filename in _METADATA_FILES:
            continue

        filepath = os.path.join(function_result_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (IOError, json.JSONDecodeError):
            continue

        if not data.get("end_flag"):
            continue

        function_name = data.get("function_name", filename[:-5])
        functionality_list = data.get("functionality_list") or []

        cvs = []
        seen = set()
        for entry in functionality_list:
            norm = _normalize_functionality_entry(entry)
            if norm is None:
                continue
            key = _dict_to_tuple(norm)
            if key in seen:
                continue
            seen.add(key)
            cvs.append(norm)

        if not cvs:
            continue

        for cv in cvs:
            direction = cv.get("direction")
            if direction == "get":
                get_map[function_name].append(cv)
            elif direction == "put":
                put_map[function_name].append(cv)
            elif direction == "set":
                set_map[function_name].append(cv)

    return get_map, put_map, set_map


def split_type_chain(chain):
    if not chain:
        return []
    return [p for p in chain.split("--") if p]


def type_chain_lcs(chain_a, chain_b):
    """Return the length of the longest common subsequence of type-chain parts."""
    parts_a = split_type_chain(chain_a)
    parts_b = split_type_chain(chain_b)
    m, n = len(parts_a), len(parts_b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m):
        for j in range(n):
            if parts_a[i] == parts_b[j]:
                dp[i + 1][j + 1] = dp[i][j] + 1
            else:
                dp[i + 1][j + 1] = max(dp[i][j + 1], dp[i + 1][j])
    return dp[m][n]


def _lcs_parts(parts_a, parts_b):
    """Return the actual LCS parts (not just length)."""
    m, n = len(parts_a), len(parts_b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m):
        for j in range(n):
            if parts_a[i] == parts_b[j]:
                dp[i + 1][j + 1] = dp[i][j] + 1
            else:
                dp[i + 1][j + 1] = max(dp[i][j + 1], dp[i + 1][j])

    # Backtrack
    lcs_parts = []
    i, j = m, n
    while i > 0 and j > 0:
        if parts_a[i - 1] == parts_b[j - 1]:
            lcs_parts.append(parts_a[i - 1])
            i -= 1
            j -= 1
        elif dp[i - 1][j] >= dp[i][j - 1]:
            i -= 1
        else:
            j -= 1
    return list(reversed(lcs_parts))


def compute_pair_score(gcv, pcv):
    """
    Score a get/put critical-variable pair based on LCS of type-chain parts.
    """
    get_chain = gcv.get("member_type_chain", "")
    put_chain = pcv.get("member_type_chain", "")

    lcs_len = type_chain_lcs(get_chain, put_chain)
    if lcs_len == 0:
        return 0.0

    get_len = len(split_type_chain(get_chain))
    put_len = len(split_type_chain(put_chain))
    max_len = max(get_len, put_len)

    base = lcs_len / max_len

    if get_chain == put_chain:
        base = 1.0

    get_path = gcv.get("member_access_path", "")
    put_path = pcv.get("member_access_path", "")
    if get_path and put_path:
        get_leaf = get_path.split(".")[-1]
        put_leaf = put_path.split(".")[-1]
        if get_leaf == put_leaf:
            base = min(1.0, base + 0.1)

    return round(base, 3)


def _best_lcs_for_function(fname, cvs, partner_map):
    """Return (best_partner, best_score, best_lcs_len) for fname against partner_map."""
    best_partner = None
    best_score = 0.0
    best_lcs_len = 0
    for pname, pcvs in partner_map.items():
        best_cv_score = 0.0
        best_cv_lcs = 0
        for cv in cvs:
            for pcv in pcvs:
                s = compute_pair_score(cv, pcv)
                if s > best_cv_score:
                    best_cv_score = s
                    best_cv_lcs = type_chain_lcs(
                        cv.get("member_type_chain", ""),
                        pcv.get("member_type_chain", "")
                    )
        if best_cv_score > best_score:
            best_score = best_cv_score
            best_partner = pname
            best_lcs_len = best_cv_lcs
    return best_partner, best_score, best_lcs_len


def build_strict_candidates(get_map, put_map, pair_id_start=0):
    """
    Step 1 — strict matching: pair get/put functions that share the exact same
    member_type_chain on at least one critical variable.
    """
    get_by_chain = defaultdict(set)
    put_by_chain = defaultdict(set)

    for fname, cvs in get_map.items():
        for cv in cvs:
            chain = cv.get("member_type_chain", "")
            if chain:
                get_by_chain[chain].add(fname)

    for fname, cvs in put_map.items():
        for cv in cvs:
            chain = cv.get("member_type_chain", "")
            if chain:
                put_by_chain[chain].add(fname)

    candidates = []
    matched_gets = set()
    matched_puts = set()
    pair_id = pair_id_start

    for chain, get_set in get_by_chain.items():
        put_set = put_by_chain.get(chain, set())
        if not put_set:
            continue

        get_list = sorted(get_set)
        put_list = sorted(put_set)

        candidates.append({
            "pair_id": pair_id,
            "schema_version": "pair-candidate.v3",
            "get_functions": get_list,
            "put_functions": put_list,
            "score": 1.0,
            "evidence": {
                "match_type": "strict",
                "type_chain_match": chain,
                "match_length": len(split_type_chain(chain))
            }
        })
        pair_id += 1
        matched_gets.update(get_list)
        matched_puts.update(put_list)

    return candidates, matched_gets, matched_puts, pair_id


def build_lcs_candidates(get_map, put_map, matched_gets, matched_puts, pair_id_start=0):
    """
    Step 2 — LCS mutual-best: for functions not strictly matched, find the best
    partner by longest common subsequence of type-chain parts. Requires mutual
    best match (both sides prefer each other).
    """
    unmatched_gets = {f: cvs for f, cvs in get_map.items() if f not in matched_gets}
    unmatched_puts = {f: cvs for f, cvs in put_map.items() if f not in matched_puts}

    if not unmatched_gets or not unmatched_puts:
        return [], pair_id_start

    # Build scored pairs
    scored_pairs = []
    for gf, gcvs in unmatched_gets.items():
        for pf, pcvs in unmatched_puts.items():
            best = 0.0
            for gcv in gcvs:
                for pcv in pcvs:
                    s = compute_pair_score(gcv, pcv)
                    if s > best:
                        best = s
            if best > 0:
                scored_pairs.append((gf, pf, best))

    if not scored_pairs:
        return [], pair_id_start

    scored_pairs.sort(key=lambda x: x[2], reverse=True)

    get_best = {}
    put_best = {}
    for gf, pf, score in scored_pairs:
        if gf not in get_best or score > get_best[gf][1]:
            get_best[gf] = (pf, score)
        if pf not in put_best or score > put_best[pf][1]:
            put_best[pf] = (gf, score)

    pair_map = defaultdict(lambda: {"get": set(), "put": set()})
    chain_sigs = {}

    for gf, (pf, score) in get_best.items():
        if put_best.get(pf, (None,))[0] == gf:
            get_chains = frozenset(
                cv.get("member_type_chain", "") for cv in unmatched_gets.get(gf, [])
            )
            put_chains = frozenset(
                cv.get("member_type_chain", "") for cv in unmatched_puts.get(pf, [])
            )
            sig = (get_chains, put_chains)
            if sig not in chain_sigs:
                chain_sigs[sig] = len(chain_sigs)
            group_key = chain_sigs[sig]
            pair_map[group_key]["get"].add(gf)
            pair_map[group_key]["put"].add(pf)

    candidates = []
    pair_id = pair_id_start
    for group_key, group in pair_map.items():
        get_list = sorted(group["get"])
        put_list = sorted(group["put"])
        if not get_list or not put_list:
            continue

        total = 0.0
        count = 0
        for gf in get_list:
            if gf in get_best:
                total += get_best[gf][1]
                count += 1
        avg_score = round(total / max(count, 1), 3)

        best_lcs_len = 0
        best_match_chain = ""
        for gf in get_list:
            for pf in put_list:
                for gcv in unmatched_gets.get(gf, []):
                    for pcv in unmatched_puts.get(pf, []):
                        ml = type_chain_lcs(
                            gcv.get("member_type_chain", ""),
                            pcv.get("member_type_chain", "")
                        )
                        if ml > best_lcs_len:
                            best_lcs_len = ml
                            best_match_chain = gcv.get("member_type_chain", "")

        candidates.append({
            "pair_id": pair_id,
            "schema_version": "pair-candidate.v3",
            "get_functions": get_list,
            "put_functions": put_list,
            "score": avg_score,
            "evidence": {
                "match_type": "lcs",
                "type_chain_match": best_match_chain,
                "match_length": best_lcs_len
            }
        })
        pair_id += 1

    # Track newly matched
    new_matched_gets = set()
    new_matched_puts = set()
    for c in candidates:
        new_matched_gets.update(c["get_functions"])
        new_matched_puts.update(c["put_functions"])

    return candidates, new_matched_gets, new_matched_puts, pair_id


def build_best_effort_candidates(get_map, put_map, matched_gets, matched_puts, pair_id_start=0):
    """
    Step 3 — best-effort: for any function still unmatched, pick the single best
    available partner by LCS score (no mutual-best requirement). Ensures every
    wrapper is paired. Marked as match_type "best_effort" to distinguish from
    higher-confidence strict/lcs matches.
    """
    unmatched_gets = {f: cvs for f, cvs in get_map.items() if f not in matched_gets}
    unmatched_puts = {f: cvs for f, cvs in put_map.items() if f not in matched_puts}

    if not unmatched_gets and not unmatched_puts:
        return [], pair_id_start

    # If only one side has unmatched, create a placeholder entry
    if not unmatched_gets:
        # All gets are matched but some puts remain — pair remaining puts with
        # the most type-similar already-matched get
        remaining_puts = dict(unmatched_puts)
        unmatched_gets = dict(get_map)  # re-evaluate against all gets
    if not unmatched_puts:
        remaining_gets = dict(unmatched_gets)
        unmatched_puts = dict(put_map)

    # Find best partner for each unmatched function
    assignments = []  # [(get_fname, put_fname, score, lcs_len), ...]

    for gf, gcvs in unmatched_gets.items():
        best_partner, best_score, best_lcs_len = _best_lcs_for_function(gf, gcvs, unmatched_puts)
        if best_partner and best_score > 0:
            assignments.append((gf, best_partner, best_score, best_lcs_len))

    for pf, pcvs in unmatched_puts.items():
        # Only add if this put wasn't already chosen by a get above
        already_in = any(a[1] == pf for a in assignments)
        if not already_in:
            best_partner, best_score, best_lcs_len = _best_lcs_for_function(pf, pcvs, unmatched_gets)
            if best_partner and best_score > 0:
                assignments.append((best_partner, pf, best_score, best_lcs_len))

    if not assignments:
        return [], pair_id_start

    # Group by (get_chain_set, put_chain_set) signature
    pair_map = defaultdict(lambda: {"get": set(), "put": set()})
    chain_sigs = {}

    for gf, pf, score, lcs_len in assignments:
        get_chains = frozenset(
            cv.get("member_type_chain", "") for cv in get_map.get(gf, [])
        )
        put_chains = frozenset(
            cv.get("member_type_chain", "") for cv in put_map.get(pf, [])
        )
        sig = (get_chains, put_chains)
        if sig not in chain_sigs:
            chain_sigs[sig] = len(chain_sigs)
        group_key = chain_sigs[sig]
        pair_map[group_key]["get"].add(gf)
        pair_map[group_key]["put"].add(pf)

    candidates = []
    pair_id = pair_id_start
    for group_key, group in pair_map.items():
        get_list = sorted(group["get"])
        put_list = sorted(group["put"])
        if not get_list or not put_list:
            continue

        # Compute average score for this group
        total = 0.0
        count = 0
        for gf in get_list:
            for pf in put_list:
                best = 0.0
                for gcv in get_map.get(gf, []):
                    for pcv in put_map.get(pf, []):
                        s = compute_pair_score(gcv, pcv)
                        if s > best:
                            best = s
                total += best
                count += 1
        avg_score = round(total / max(count, 1), 3)

        best_lcs_len = 0
        best_match_chain = ""
        for gf in get_list:
            for pf in put_list:
                for gcv in get_map.get(gf, []):
                    for pcv in put_map.get(pf, []):
                        ml = type_chain_lcs(
                            gcv.get("member_type_chain", ""),
                            pcv.get("member_type_chain", "")
                        )
                        if ml > best_lcs_len:
                            best_lcs_len = ml
                            best_match_chain = gcv.get("member_type_chain", "")

        candidates.append({
            "pair_id": pair_id,
            "schema_version": "pair-candidate.v3",
            "get_functions": get_list,
            "put_functions": put_list,
            "score": avg_score,
            "evidence": {
                "match_type": "best_effort",
                "type_chain_match": best_match_chain,
                "match_length": best_lcs_len
            }
        })
        pair_id += 1

    return candidates, pair_id


def build_set_put_candidates(set_map, put_map, pair_id_start=0):
    """
    Pair set functions (create initial reference) with put functions (release reference).
    Uses the same 3-tier strategy as get<->put pairing:
      1. strict (exact type-chain match)
      2. LCS mutual-best
      3. best-effort
    Reuses the existing build_strict_candidates/build_lcs_candidates/build_best_effort
    functions — the first argument is the "acquire/create" side, the second is the
    "release" side. All candidates are tagged with pairing_type: "set_put".
    """
    # Step 1: strict (exact type-chain match)
    strict, matched_sets, matched_puts, pair_id = \
        build_strict_candidates(set_map, put_map, pair_id_start=pair_id_start)

    # Step 2: LCS mutual-best
    lcs, new_matched_sets, new_matched_puts, pair_id = \
        build_lcs_candidates(set_map, put_map, matched_sets, matched_puts, pair_id_start=pair_id)
    matched_sets |= new_matched_sets
    matched_puts |= new_matched_puts

    # Step 3: best-effort
    best_effort, pair_id = \
        build_best_effort_candidates(set_map, put_map, matched_sets, matched_puts, pair_id_start=pair_id)

    all_candidates = strict + lcs + best_effort
    # Tag each candidate with pairing_type: "set_put"
    for c in all_candidates:
        c["evidence"]["pairing_type"] = "set_put"
    return sorted(all_candidates, key=lambda item: item["score"], reverse=True)


def build_pair_candidates(function_result_dir):
    get_map, put_map, set_map = collect_critical_variables(function_result_dir)

    # Step 1: strict (exact type-chain match)
    strict_candidates, matched_gets, matched_puts, pair_id = \
        build_strict_candidates(get_map, put_map, pair_id_start=0)

    # Step 2: LCS mutual-best (longest common subsequence)
    lcs_candidates, new_matched_gets, new_matched_puts, pair_id = \
        build_lcs_candidates(get_map, put_map, matched_gets, matched_puts, pair_id_start=pair_id)
    matched_gets |= new_matched_gets
    matched_puts |= new_matched_puts

    # Step 3: best-effort (guarantee every wrapper is paired)
    best_effort_candidates, pair_id = \
        build_best_effort_candidates(get_map, put_map, matched_gets, matched_puts, pair_id_start=pair_id)

    # Set->put pairing (create initial reference → release reference)
    set_put_candidates = build_set_put_candidates(set_map, put_map, pair_id_start=pair_id)

    all_candidates = strict_candidates + lcs_candidates + best_effort_candidates + set_put_candidates
    return sorted(all_candidates, key=lambda item: item["score"], reverse=True)


def save_pair_candidates(function_result_dir, candidates):
    output_path = os.path.join(function_result_dir, PAIR_CANDIDATE_FILENAME)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(candidates, f, indent=2, ensure_ascii=False)
    return output_path


def get_function_pairs(function_result_dir):
    candidates = build_pair_candidates(function_result_dir)
    save_pair_candidates(function_result_dir, candidates)
    return candidates


if __name__ == "__main__":
    function_result_dir = os.environ.get(
        "REFCOUNT_FUNCTION_RESULT_DIR",
        os.path.join(os.environ.get("REFCOUNT_DATA_DIR", "./data"), "FunctionResult", "default")
    )
    candidates = get_function_pairs(function_result_dir)
    for candidate in candidates:
        print(json.dumps(candidate, indent=2, ensure_ascii=False))
