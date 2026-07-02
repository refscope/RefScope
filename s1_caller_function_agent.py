from typing import Dict, Any
from callgraph import get_callers
from accurate_func_locator import AccurateFuncLocator
import requests
import json
import os
import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# DWARF 类型链提取 (pahole/DWARF 87% 成功率 + LLM 兜底)
try:
    from cross_validator import extract_type_chain as dwarf_extract
    HAS_DWARF = True
except ImportError:
    HAS_DWARF = False

# 全局缓存
_FUNCTION_DATA_CACHE: Dict[str, Any] = {}
_FUNC_LOCATOR: AccurateFuncLocator = None
_USE_CTAGS_FALLBACK: bool = False
PROGRAME_DIR = os.path.dirname(os.path.abspath(__file__))
WRAPPER_TRACE_FILENAME = "wrapper_stage_traces.json"

# 全局计时统计
_TIMING_LOG: Dict[str, list] = {}

# 内存缓存 wrapper_stage_traces (避免每阶段都读写完整 JSON)
_TRACE_CACHE: Dict[str, Any] = None
_TRACE_DIRTY: bool = False

# 并行处理配置
_MAX_WORKERS = 32       # 最大并发 LLM 调用数
_BATCH_SIZE = 32      # 每波最大函数数（超过则分批）

# 线程安全锁
_TRACE_LOCK = threading.Lock()
_TIMING_LOCK = threading.Lock()
_DB_LOCK = threading.Lock()


class Agent:
    def __init__(self, api_key, api_url, model="gpt-5"):
        # 配置信息
        normalized_api_url = api_url.rstrip("/")
        if not normalized_api_url.endswith("/chat/completions"):
            normalized_api_url = f"{normalized_api_url}/chat/completions"

        self.CONFIG = {
            "api_key": api_key,
            "api_url": normalized_api_url
        }
        self.headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
        }

        self.prompt={
                "model": model,
                "messages": [],
                "temperature": 0,
                "top_p": 1,
                "max_tokens": 104800,
                "stream": False,
                "n": 1
                }


class CF_Agent(Agent):
    def __init__(self, api_key, api_url, model="gpt-5"):
        Agent.__init__(self, api_key, api_url, model)

    def build_prompt(self, prompt_filename, user_content):
        with open(os.path.join(PROGRAME_DIR, prompt_filename), "r") as fp:
            user_prompt = fp.read()
        with open(os.path.join(PROGRAME_DIR, "./template_sys.prompt"), "r") as fp:
            sys_prompt = fp.read()

        data = [
            {
                "role": "system",
                "content": sys_prompt
            },
            {
                "role": "user",
                "content": user_prompt.format(**user_content)
            }
        ]
        self.prompt["messages"] = data

    def build_judge_prompt(self, target_func_name, target_func_code, callee_get_put_func_info, fetched_code=""):
        self.build_prompt("template_judge.prompt", {
            "target_func_name": target_func_name,
            "target_func_code": target_func_code,
            "callee_get_put_func_info": callee_get_put_func_info,
            "fetched_code": fetched_code
        })

    def build_extract_prompt(self, target_func_name, target_func_code, callee_get_put_func_info, fetched_callee_code=""):
        self.build_prompt("template_extract.prompt", {
            "target_func_name": target_func_name,
            "target_func_code": target_func_code,
            "callee_get_put_func_info": callee_get_put_func_info,
            "fetched_callee_code": fetched_callee_code
        })

    def build_check_prompt(self, target_func_name, target_func_code, callee_get_put_func_info, candidate_result_list):
        self.build_prompt("template_check.prompt", {
            "target_func_name": target_func_name,
            "target_func_code": target_func_code,
            "callee_get_put_func_info": callee_get_put_func_info,
            "candidate_result_list": json.dumps(candidate_result_list, ensure_ascii=False, indent=2)
        })

    def build_expand_prompt(self, target_func_name, target_func_code, wrapper_judgment, validated_result_list):
        self.build_prompt("template_expand.prompt", {
            "target_func_name": target_func_name,
            "target_func_code": target_func_code,
            "wrapper_judgment": json.dumps(wrapper_judgment, ensure_ascii=False, indent=2),
            "validated_result_list": json.dumps(validated_result_list, ensure_ascii=False, indent=2)
        })

    def build_reevaluate_prompt(self, target_func_name, target_func_code, callee_get_put_func_info,
                                 candidate_result_list, check_reason):
        self.build_prompt("template_reevaluate.prompt", {
            "target_func_name": target_func_name,
            "target_func_code": target_func_code,
            "callee_get_put_func_info": callee_get_put_func_info,
            "candidate_result_list": json.dumps(candidate_result_list, ensure_ascii=False, indent=2),
            "check_reason": check_reason
        })


def format_callee_get_put_func_info(callee_get_put_func_info_list):
    callee_get_put_func_info = ""
    count = 1
    for item in callee_get_put_func_info_list:
        callee_get_put_func_info += f"{count}. The function {item['callee_function_name']} in the implementation is a {item['get_or_put']} function for its {item['location']} index {item['index']}, its member-access path is {item['member_access_path']}, which is of type {item['member_type_chain']}.\n"
        # Append semantic contract if available
        contract = item.get('contract_summary', '')
        if contract:
            callee_get_put_func_info += f"   Contract: {contract}\n"
        conditionality = item.get('conditionality', '')
        if conditionality:
            callee_get_put_func_info += f"   Conditionality: {conditionality}\n"
        count += 1
    return callee_get_put_func_info


def dict_to_tuple(d):
    return tuple(sorted(d.items()))


def tuple_to_dict(t):
    return dict(t)


def _strip_struct_keywords(type_chain: str) -> str:
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


def extract_message_content(choice):
    message = choice.get("message", {})
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
                elif "text" in item:
                    text_parts.append(str(item.get("text", "")))
            elif isinstance(item, str):
                text_parts.append(item)
        return "\n".join(part for part in text_parts if part)
    return str(content)


def _strip_json_fences(text: str) -> str:
    """去掉 ```json ... ``` 或 ``` ... ``` 包裹，提取纯 JSON 文本。"""
    text = text.strip()
    for prefix in ("```json", "```JSON", "```"):
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
            if text.endswith("```"):
                text = text[:-3].strip()
            break
    return text


def extract_json_candidate(content):
    # 1. 优先匹配 <OUTPUT JSON>...</OUTPUT JSON> 标签
    tagged_match = re.search(r"<OUTPUT JSON>\s*(.*?)\s*</OUTPUT JSON>", content, re.DOTALL)
    if tagged_match:
        return _strip_json_fences(tagged_match.group(1))

    # 2. 匹配 ```json ... ``` 代码块
    fenced_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL | re.IGNORECASE)
    if fenced_match:
        return fenced_match.group(1).strip()

    # 3. 匹配 ``` ... ``` 通用代码块
    generic_fence_match = re.search(r"```\s*(.*?)\s*```", content, re.DOTALL)
    if generic_fence_match:
        return generic_fence_match.group(1).strip()

    # 4. 尝试直接当 JSON 解析
    stripped = content.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        return stripped

    # 5. 从文本中提取第一个 { ... } 块
    first_brace = stripped.find("{")
    last_brace = stripped.rfind("}")
    if first_brace != -1 and last_brace != -1 and first_brace < last_brace:
        return stripped[first_brace:last_brace + 1].strip()

    return stripped


def request_agent_json(cf_agent):
    try:
        http_response = requests.post(
            cf_agent.CONFIG["api_url"],
            headers=cf_agent.headers,
            json=cf_agent.prompt,
            timeout=300,
        )
        http_response.raise_for_status()
    except requests.RequestException as exc:
        raise ValueError(
            f"HTTP request failed for {cf_agent.CONFIG['api_url']}: {exc}"
        ) from exc

    try:
        response = http_response.json()
    except ValueError as exc:
        raise ValueError(f"Non-JSON API response: {http_response.text[:1000]}") from exc

    try:
        choice = response["choices"][0]
    except Exception as exc:
        raise ValueError(f"API Response Error: {response}") from exc

    content = extract_message_content(choice)
    json_result = extract_json_candidate(content)

    try:
        parsed = json.loads(json_result)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Failed to parse model JSON output. "
            f"Extracted candidate: {json_result[:1000]} | Raw content: {content[:2000]}"
        ) from exc

    return {
        "raw_response": response,
        "parsed": parsed,
        "prompt": cf_agent.prompt,
        "content": content,
        "json_candidate": json_result,
    }


def run_wrapper_judge_iterative(api_key, api_url, model, target_func_name, target_func_code, callee_get_put_func_info):
    """Iteratively fetch requested source code until the model has enough info to judge.

    The model can request additional function implementations via the
    need_more_info / requested_functions protocol, up to 5 rounds.
    """
    cf_agent = CF_Agent(api_key, api_url, model)
    fetched_code = {}
    max_iterations = 5

    for iteration in range(max_iterations):
        # Format fetched code for prompt
        fetched_code_str = ""
        if fetched_code:
            for name, code in fetched_code.items():
                fetched_code_str += f"\n// Fetched implementation of: {name}\n{code}\n"

        cf_agent.build_judge_prompt(
            target_func_name, target_func_code,
            callee_get_put_func_info, fetched_code_str
        )
        result = request_agent_json(cf_agent)
        parsed = result.get("parsed", {})

        need_more = parsed.get("need_more_info", False)
        if not need_more:
            return result

        requested = parsed.get("requested_functions", [])
        if not requested:
            return result

        newly_fetched = 0
        for func_name in requested:
            if func_name not in fetched_code:
                code, _ = find_func_source_code(func_name, _FUNCTION_DATA_CACHE)
                fetched_code[func_name] = code if code else f"// Implementation of {func_name} not found"
                newly_fetched += 1

        if newly_fetched == 0:
            print(f"    [Judge Iter {iteration+1}] All requested functions already fetched, forcing final judgment.")
            cf_agent.build_judge_prompt(
                target_func_name, target_func_code,
                callee_get_put_func_info, fetched_code_str
            )
            return request_agent_json(cf_agent)

        print(f"    [Judge Iter {iteration+1}] Fetched {newly_fetched} function(s): "
              f"{[c for c in requested if c in fetched_code]}")

    # Max iterations reached, return last result
    print(f"    [Judge] Max iterations ({max_iterations}) reached, returning current result.")
    return result


# Backward-compatible alias
def run_wrapper_judge(api_key, api_url, model, target_func_name, target_func_code, callee_get_put_func_info):
    """Simple one-shot judge (kept for backward compatibility)."""
    return run_wrapper_judge_iterative(api_key, api_url, model, target_func_name, target_func_code, callee_get_put_func_info)


def run_path_extract(api_key, api_url, model, target_func_name, target_func_code, callee_get_put_func_info):
    """Simple one-shot extract (kept for backward compatibility)."""
    cf_agent = CF_Agent(api_key, api_url, model)
    cf_agent.build_extract_prompt(target_func_name, target_func_code, callee_get_put_func_info)
    return request_agent_json(cf_agent)


def run_path_extract_iterative(api_key, api_url, model, target_func_name, target_func_code, callee_get_put_func_info):
    """Iteratively fetch callee implementations until model has enough info to trace complete type chains."""
    cf_agent = CF_Agent(api_key, api_url, model)
    fetched_callee_code = {}
    max_iterations = 5

    for iteration in range(max_iterations):
        # Format fetched callee code for prompt
        fetched_code_str = ""
        if fetched_callee_code:
            for name, code in fetched_callee_code.items():
                fetched_code_str += f"\n// Implementation of callee: {name}\n{code}\n"

        cf_agent.build_extract_prompt(
            target_func_name, target_func_code,
            callee_get_put_func_info, fetched_code_str
        )
        result = request_agent_json(cf_agent)
        parsed = result.get("parsed", {})

        need_more = parsed.get("need_more_info", False)
        if not need_more:
            return result

        requested = parsed.get("requested_callees", [])
        if not requested:
            return result

        newly_fetched = 0
        for callee_name in requested:
            if callee_name not in fetched_callee_code:
                code, _ = find_func_source_code(callee_name, _FUNCTION_DATA_CACHE)
                fetched_callee_code[callee_name] = code if code else f"// Implementation of {callee_name} not found"
                newly_fetched += 1

        if newly_fetched == 0:
            print(f"    [Extract Iter {iteration+1}] All requested callees already fetched, forcing extraction.")
            cf_agent.build_extract_prompt(
                target_func_name, target_func_code,
                callee_get_put_func_info, fetched_code_str
            )
            return request_agent_json(cf_agent)

        print(f"    [Extract Iter {iteration+1}] Fetched {newly_fetched} callee(s): "
              f"{[c for c in requested if c in fetched_callee_code]}")

    # Max iterations reached, return last result
    print(f"    [Extract] Max iterations ({max_iterations}) reached, returning current result.")
    return result


def run_consistency_check(api_key, api_url, model, target_func_name, target_func_code, callee_get_put_func_info, candidate_result_list):
    cf_agent = CF_Agent(api_key, api_url, model)
    cf_agent.build_check_prompt(target_func_name, target_func_code, callee_get_put_func_info, candidate_result_list)
    return request_agent_json(cf_agent)


def run_expand_decision(api_key, api_url, model, target_func_name, target_func_code, wrapper_judgment, validated_result_list):
    cf_agent = CF_Agent(api_key, api_url, model)
    cf_agent.build_expand_prompt(target_func_name, target_func_code, wrapper_judgment, validated_result_list)
    return request_agent_json(cf_agent)


def run_conflict_resolution(api_key, api_url, model, target_func_name, target_func_code,
                            callee_get_put_func_info, candidate_result_list, check_reason):
    cf_agent = CF_Agent(api_key, api_url, model)
    cf_agent.build_reevaluate_prompt(target_func_name, target_func_code, callee_get_put_func_info,
                                     candidate_result_list, check_reason)
    return request_agent_json(cf_agent)




def _verify_source_contains_function(target_func_name, source_code):
    """
    Verify that source_code actually contains the target function definition or body.
    Returns (is_valid: bool, reason: str).
    """
    if not source_code:
        return False, "empty_source"
    if source_code == "Cannot find function implementation.":
        return False, "read_error"

    if target_func_name not in source_code:
        return False, "name_not_found"

    # Check for function definition or call pattern: func_name\s*\(
    if not re.search(r'\b' + re.escape(target_func_name) + r'\s*\(', source_code):
        return False, "no_function_pattern"

    return True, "ok"


def read_func_implementation(file_path, start_line, end_line, expand_window=0):
    """
    Read function implementation from file_path between start_line and end_line.
    If expand_window > 0, read extra lines before and after the reported range
    to tolerate small location errors.
    """
    with open(file_path, "r") as fp:
        all_lines = fp.readlines()

    read_start = max(0, start_line - 1 - expand_window)
    read_end = min(len(all_lines), end_line + expand_window)

    if start_line - 1 >= len(all_lines):
        print(f"Warning: start_line {start_line} exceeds file length {len(all_lines)} in {file_path}")
        return "Cannot find function implementation."

    implementation_lines = all_lines[read_start:read_end]
    return "".join(implementation_lines)


def find_func_source_code(target_func_name, _FUNCTION_DATA_CACHE):
    """
    Return the source code AND file path of a target function for prompt context.

    Returns: (source_code: str, file_path: str | None)

    Strategy (layered):
    1. Primary:   AccurateFuncLocator (cscope-L1 + state-machine brace matching + strict verify)
    2. Optional:  _FUNCTION_DATA_CACHE (ctags-based func_loc.json + expand_window retry)
                   Controlled by _USE_CTAGS_FALLBACK (default: False)
    """
    # --- Primary: AccurateFuncLocator ---
    locator_result = None
    source_file = None
    if _FUNC_LOCATOR is not None and _FUNC_LOCATOR.cscope_db_exists():
        locator_result = _FUNC_LOCATOR.find_function_source(target_func_name)
        source_file = locator_result.get("file_path") if locator_result else None
        if locator_result["is_definition"] and locator_result["confidence"] in ("high", "medium"):
            return locator_result["source_code"], source_file
        elif locator_result["source_code"]:
            if not _USE_CTAGS_FALLBACK:
                # 回退禁用时，直接返回 locator 的结果（即使低置信度）
                print(f"Note: AccurateFuncLocator found {target_func_name} "
                      f"with confidence={locator_result['confidence']} "
                      f"(ctags fallback disabled, using locator result).")
                return locator_result["source_code"], source_file
            print(f"Note: AccurateFuncLocator found {target_func_name} "
                  f"with confidence={locator_result['confidence']}, "
                  f"falling back to cache for verification.")

    # --- Optional fallback: cache-based ctags lookup ---
    if not _USE_CTAGS_FALLBACK:
        if locator_result and locator_result["source_code"]:
            return locator_result["source_code"], source_file
        return "", None

    func_infos = _FUNCTION_DATA_CACHE.get("functions", {}).get(target_func_name)
    if not func_infos:
        if locator_result and locator_result["source_code"]:
            return locator_result["source_code"], source_file
        return "", None

    verified_sources = []
    for func_info in func_infos:
        file_path = func_info.get("file_path")
        start_line = func_info.get("start_line")
        end_line = func_info.get("end_line")

        if not (file_path and start_line and end_line):
            continue

        source = read_func_implementation(file_path, start_line, end_line)
        is_valid, reason = _verify_source_contains_function(target_func_name, source)
        if is_valid:
            is_c_file = file_path.endswith(".c")
            verified_sources.append((source, is_c_file, file_path))
        else:
            print(f"Warning: func_loc entry for {target_func_name} in {file_path} "
                  f"lines {start_line}-{end_line} failed verification ({reason}). "
                  f"Trying expanded window.")
            expanded_source = read_func_implementation(
                file_path, start_line, end_line, expand_window=30
            )
            is_valid2, reason2 = _verify_source_contains_function(target_func_name, expanded_source)
            if is_valid2:
                is_c_file = file_path.endswith(".c")
                verified_sources.append((expanded_source, is_c_file, file_path))
                print(f"  -> expanded window succeeded for {target_func_name} in {file_path}")

    if not verified_sources:
        print(f"Error: No verified source code found for {target_func_name} "
              f"across {len(func_infos)} func_loc entries.")
        return "", None

    c_sources = [s for s, c, p in verified_sources if c]
    h_sources = [s for s, c, p in verified_sources if not c]

    selected = []
    selected_path = None
    if c_sources:
        selected.append(c_sources[0])
        selected_path = [p for s, c, p in verified_sources if c][0]
    if h_sources:
        selected.append(h_sources[0])
        if not selected_path:
            selected_path = [p for s, c, p in verified_sources if not c][0]
    if not selected:
        selected = [verified_sources[0][0]]
        selected_path = verified_sources[0][2]

    return "\n".join(selected), selected_path


def is_callee_get_put_func_info_list_same(callee_get_put_func_info_list_1_dup, callee_get_put_func_info_list_2_dup):
    """
    Compare two callee get/put info lists for equality.
    The items are dicts containing keys like:
      'callee_function_name', 'get_or_put', 'parameter_index', 'member_type_chain'
    Return True if lists are equal (order and content).
    """

    # print(callee_get_put_func_info_list_1_dup)
    # print(callee_get_put_func_info_list_2_dup)

    if callee_get_put_func_info_list_1_dup is None or callee_get_put_func_info_list_2_dup is None:
        return False
    
    unique_tuples = set(dict_to_tuple(d) for d in callee_get_put_func_info_list_1_dup)
    callee_get_put_func_info_list_1 = [tuple_to_dict(t) for t in unique_tuples]

    unique_tuples = set(dict_to_tuple(d) for d in callee_get_put_func_info_list_2_dup)
    callee_get_put_func_info_list_2 = [tuple_to_dict(t) for t in unique_tuples]

    if len(callee_get_put_func_info_list_1) != len(callee_get_put_func_info_list_2):
        return False
    
    # Compare sorted versions to ignore order
    def key_func(x):
        return (str(x.get("callee_function_name", "")),
                str(x.get("get_or_put", "")),
                str(x.get("index", "")),
                str(x.get("location", "")),
                str(x.get("member_access_path", "")),
                str(x.get("member_type_chain", "")))
    
    sorted1 = sorted(callee_get_put_func_info_list_1, key=key_func)
    sorted2 = sorted(callee_get_put_func_info_list_2, key=key_func)

    for i1, i2 in zip(sorted1, sorted2):
        if i1 != i2:
            return False
    return True


def is_target_func_in_db(target_func_name, callee_get_put_func_info_list, FunctionResult_dir):
    """
    Checks whether the target function has been analyzed and stored in DB.
    Returns:
      - "not_in_db": if function is not recorded (never analyzed), or only has a
        minimal callee-info stub created by save_callee_to_db.
      - "need_update": if function is in DB but callee_get_put_func_info_list differs
        from the snapshot taken at the last analysis time.
      - "not_changed": if function is already analyzed and no update needed.
    """

    # Compose DB file path for storing function results
    db_file_path = os.path.join(FunctionResult_dir, f"{target_func_name}.json")
    if not os.path.exists(db_file_path):
        return "not_in_db"

    # Load existing entry
    try:
        with open(db_file_path, "r") as f:
            function_entry = json.load(f)
    except (IOError, json.JSONDecodeError):
        return "not_in_db"

    # A minimal stub (no end_flag) was created by save_callee_to_db — not yet analyzed
    if "end_flag" not in function_entry:
        return "not_in_db"

    # Compare against the FROZEN snapshot from last analysis — NOT against the live
    # callee_func_info_list (which save_callee_to_db may have updated since).
    old_callee_snapshot = function_entry.get("analyzed_callee_snapshot",
                                             function_entry.get("callee_func_info_list", []))

    if not is_callee_get_put_func_info_list_same(old_callee_snapshot, callee_get_put_func_info_list):
        return "need_update"
    return "not_changed"


def normalize_functionality_list(functionality_list):
    normalized = []
    for functionality in functionality_list:
        if len(functionality) < 5:
            continue
        location = "parameter" if functionality[1] == "para" else functionality[1]
        normalized.append({
            "direction": functionality[0],
            "location": location,
            "index": functionality[2],
            "member_access_path": functionality[3],
            "member_type_chain": functionality[4]
        })
    unique_tuples = set(dict_to_tuple(d) for d in normalized)
    return [tuple_to_dict(t) for t in unique_tuples]


def get_trace_file_path(FunctionResult_dir):
    return os.path.join(FunctionResult_dir, WRAPPER_TRACE_FILENAME)


def _init_trace_cache(FunctionResult_dir):
    """初始化 trace 内存缓存 — 只从磁盘读取一次。"""
    global _TRACE_CACHE, _TRACE_DIRTY
    _TRACE_CACHE = None  # 先重置让 load 走磁盘路径
    _TRACE_CACHE = load_wrapper_stage_traces(FunctionResult_dir)
    _TRACE_DIRTY = False
    print("Trace cache initialized in memory.")


def _flush_trace_cache(FunctionResult_dir):
    """将 trace 缓存写回磁盘（仅在 dirty 时）。"""
    global _TRACE_DIRTY
    if not _TRACE_DIRTY or _TRACE_CACHE is None:
        return
    os.makedirs(FunctionResult_dir, exist_ok=True)
    t0 = time.time()
    with open(get_trace_file_path(FunctionResult_dir), "w") as f:
        json.dump(_TRACE_CACHE, f, indent=2)
    _TRACE_DIRTY = False
    print(f"Trace cache flushed to disk ({time.time() - t0:.2f}s).")


def load_wrapper_stage_traces(FunctionResult_dir):
    if _TRACE_CACHE is not None:
        return _TRACE_CACHE
    trace_file_path = get_trace_file_path(FunctionResult_dir)
    if not os.path.exists(trace_file_path):
        return {"functions": {}}
    try:
        with open(trace_file_path, "r") as f:
            traces = json.load(f)
    except (IOError, json.JSONDecodeError):
        return {"functions": {}}
    traces.setdefault("functions", {})
    return traces


def save_wrapper_stage_traces(traces, FunctionResult_dir):
    global _TRACE_CACHE, _TRACE_DIRTY
    _TRACE_CACHE = traces
    _TRACE_DIRTY = True


def update_wrapper_stage_trace(FunctionResult_dir, target_func_name, stage_name, payload):
    """（线程安全）"""
    with _TRACE_LOCK:
        traces = load_wrapper_stage_traces(FunctionResult_dir)
        function_trace = traces["functions"].setdefault(target_func_name, {
            "function_name": target_func_name,
            "stages": {},
            "final": {}
        })
        function_trace["stages"][stage_name] = payload
        save_wrapper_stage_traces(traces, FunctionResult_dir)


def finalize_wrapper_trace(FunctionResult_dir, target_func_name, final_payload):
    """（线程安全）"""
    with _TRACE_LOCK:
        traces = load_wrapper_stage_traces(FunctionResult_dir)
        function_trace = traces["functions"].setdefault(target_func_name, {
            "function_name": target_func_name,
            "stages": {},
            "final": {}
        })
        function_trace["final"] = final_payload
        save_wrapper_stage_traces(traces, FunctionResult_dir)


def find_all_related_callee_functions(target_func_name, FunctionResult_dir):
    """
    Retrieve from DB the list of callee get/put function info for target function.
    Reads callee_func_info_list from the per-function JSON (previously stored via
    save_callee_to_db or save_functionality_to_db).
    Return list of dicts with keys:
      'callee_function_name', 'get_or_put', 'parameter_index', 'member_type_chain'
    """

    db_file_path = os.path.join(FunctionResult_dir, f"{target_func_name}.json")
    if not os.path.exists(db_file_path):
        return []

    try:
        with open(db_file_path, "r") as f:
            function_entry = json.load(f)
    except (IOError, json.JSONDecodeError):
        return []

    return function_entry.get("callee_func_info_list", [])


def save_functionality_to_db(target_func_name, functionality_list, callee_get_put_func_info_list, end_flag, is_update, FunctionResult_dir, purity=None, stages=None, final=None, conditionality=None, must_check=None, retry_on_failure=None, retry_reason=None, contract_summary=None):
    """
    Save/Update the target function analysis to DB.
    Thread-safe: uses _DB_LOCK and merges callee_func_info_list with any entries
    that may have been concurrently added by save_callee_to_db.
    """
    # Strip struct/enum/union keywords from type chains
    clean_functionality_list = []
    for entry in functionality_list:
        entry = list(entry)
        if len(entry) >= 5:
            entry[4] = _strip_struct_keywords(entry[4])
        clean_functionality_list.append(entry)

    os.makedirs(FunctionResult_dir, exist_ok=True)
    db_file_path = os.path.join(FunctionResult_dir, f"{target_func_name}.json")

    # Freeze the original callee list as the snapshot (what the model actually analyzed)
    original_tuples = set(dict_to_tuple(d) for d in callee_get_put_func_info_list)
    analyzed_snapshot = [tuple_to_dict(t) for t in original_tuples]
    merged_tuples = set(original_tuples)

    with _DB_LOCK:
        # Merge with any callee entries that save_callee_to_db may have added concurrently
        if os.path.exists(db_file_path):
            try:
                with open(db_file_path, "r") as f:
                    existing_entry = json.load(f)
            except (IOError, json.JSONDecodeError):
                existing_entry = {}
            existing_callee_list = existing_entry.get("callee_func_info_list", [])
            for d in existing_callee_list:
                t = dict_to_tuple(d)
                merged_tuples.add(t)

        unique_callee_get_put_func_info_list = [tuple_to_dict(t) for t in merged_tuples]

        entry = {
            "function_name": target_func_name,
            "end_flag": end_flag,
            "functionality_list": clean_functionality_list,
            "is_update": is_update in ("not_in_db", "need_update"),
            "purity": purity,
            "callee_func_info_list": unique_callee_get_put_func_info_list,
            "analyzed_callee_snapshot": analyzed_snapshot,
            "conditionality": conditionality,
            "must_check": must_check,
            "retry_on_failure": retry_on_failure,
            "retry_reason": retry_reason,
            "contract_summary": contract_summary,
        }

        if stages is not None:
            entry["stages"] = stages
        if final is not None:
            entry["final"] = final

        with open(db_file_path, "w") as f:
            json.dump(entry, f, indent=2, ensure_ascii=False)


def save_callee_to_db(caller_func_name, functionality_list, target_func_name, FunctionResult_dir,
                      contract_summary="", conditionality="", must_check=None, retry_on_failure=None):
    """（线程安全 — 多个线程可能同时写同一个 caller 的 per-function JSON）

    将 callee get/put 信息写入 caller 的 per-function JSON 的 callee_func_info_list 字段。
    如果 caller 尚未分析（JSON 不存在），创建仅含 callee_func_info_list 的最小条目。
    如果 caller 已分析，保留所有已有字段，仅合并 callee_func_info_list。
    """
    new_callee_entries = []
    for functionality in functionality_list:
        elemt = {}
        elemt['callee_function_name'] = target_func_name
        elemt['get_or_put'] = functionality[0]
        if functionality[1] == "para":
            elemt["location"] = "parameter"
        else:
            elemt["location"] = functionality[1]
        elemt['index'] = functionality[2]
        elemt['member_access_path'] = functionality[3]
        elemt['member_type_chain'] = _strip_struct_keywords(functionality[4])
        elemt['contract_summary'] = contract_summary
        elemt['conditionality'] = conditionality
        if must_check is not None:
            elemt['must_check'] = must_check
        if retry_on_failure is not None:
            elemt['retry_on_failure'] = retry_on_failure
        new_callee_entries.append(elemt)

    db_file_path = os.path.join(FunctionResult_dir, f"{caller_func_name}.json")

    with _DB_LOCK:
        # Read existing entry, preserving all fields
        if os.path.exists(db_file_path):
            try:
                with open(db_file_path, "r") as f:
                    entry = json.load(f)
            except (IOError, json.JSONDecodeError):
                entry = {"function_name": caller_func_name}
        else:
            entry = {"function_name": caller_func_name}

        existing_callee_list = entry.get("callee_func_info_list", [])
        merged_callee_list = existing_callee_list + new_callee_entries

        unique_tuples = set(dict_to_tuple(d) for d in merged_callee_list)
        entry["callee_func_info_list"] = [tuple_to_dict(t) for t in unique_tuples]

        os.makedirs(FunctionResult_dir, exist_ok=True)
        with open(db_file_path, "w") as f:
            json.dump(entry, f, indent=2, ensure_ascii=False)
    


def get_endflag(target_func_name, FunctionResult_dir):
    db_file_path = os.path.join(FunctionResult_dir, f"{target_func_name}.json")
    if not os.path.exists(db_file_path):
        return False
    try:
        with open(db_file_path, "r") as f:
            function_entry = json.load(f)
    except (IOError, json.JSONDecodeError):
        return False
    return function_entry.get("end_flag", False)


def _record_timing(func_name: str, stage: str, elapsed: float) -> float:
    """记录一个阶段的耗时到全局 _TIMING_LOG，返回 elapsed 以便累加。（线程安全）"""
    global _TIMING_LOG
    with _TIMING_LOCK:
        _TIMING_LOG.setdefault(f"{func_name}|{stage}", []).append(elapsed)
    return elapsed


def _print_timing_summary(wall_clock_seconds=None):
    """打印阶段耗时汇总（最终版，含头部）。"""
    print("\n" + "=" * 65)
    print("TIMING SUMMARY (FINAL)")
    print("=" * 65)
    _print_timing_summary_partial(wall_clock_seconds)
    print("=" * 65 + "\n")


def _print_timing_summary_partial(wall_clock_seconds=None):
    """打印阶段耗时汇总的表格部分（不含头部和尾部装饰线）。

    用于进度检查点，格式与 _print_timing_summary 的表格完全一致。
    """
    grouped: Dict[str, list] = {}
    # 在锁内拍快照，避免 worker 线程同时写入导致 "dictionary changed size during iteration"
    with _TIMING_LOCK:
        items = list(_TIMING_LOG.items())
    for key, vals in items:
        func, stage = key.split("|", 1)
        grouped.setdefault(stage, []).extend(vals)

    total_all = 0.0
    stage_order = ["source_lookup", "judge", "extract", "check",
                   "reevaluate", "io_save", "callers", "overhead"]
    for stage in stage_order:
        vals = grouped.pop(stage, [])
        if not vals:
            continue
        total_s = sum(vals)
        avg_s = total_s / len(vals)
        total_all += total_s
        print(f"  {stage:20s}  count={len(vals):4d}  total={total_s:8.2f}s  avg={avg_s:.2f}s")
    for stage, vals in sorted(grouped.items()):
        total_s = sum(vals)
        avg_s = total_s / len(vals)
        total_all += total_s
        print(f"  {stage:20s}  count={len(vals):4d}  total={total_s:8.2f}s  avg={avg_s:.2f}s")
    print(f"  {'─' * 65}")
    print(f"  {'TOTAL (aggregate thread time)':30s} {total_all:8.2f}s")
    if wall_clock_seconds is not None:
        parallelism = total_all / max(wall_clock_seconds, 0.1)
        print(f"  {'Wall-clock (elapsed so far)':30s} {wall_clock_seconds:8.2f}s")
        print(f"  {'Effective parallelism':30s} {parallelism:8.1f}x")


def _analyze_single_function(target_func_name, api_key, api_url, model, linux_dir, FunctionResult_dir, queue_remain=0):
    """分析单个函数。返回 (callers_list, error_str)。线程安全。"""
    t_func_start = time.time()
    t_staged = 0.0
    callers_list = []
    error_str = None
    stages = {}       # per-stage parsed results for per-function JSON
    final_payload = {}

    print(f"[{target_func_name}] Analyzing... (queue remain: {queue_remain})")

    callee_get_put_func_info_list = find_all_related_callee_functions(target_func_name, FunctionResult_dir)
    is_update = is_target_func_in_db(target_func_name, callee_get_put_func_info_list, FunctionResult_dir)
    if is_update == "not_changed":
        print(f"[{target_func_name}] Already analyzed and up-to-date. Skipping.")
        # 已分析过且未变化 —— 不再重复返回 callers。
        # 该函数的 callers 在首次分析时已经入队，重复入队会导致死循环
        # （A→B→A 的循环依赖关系中，两者互相将对方重新入队）。
        t_total = time.time() - t_func_start
        _record_timing(target_func_name, "overhead", t_total - t_staged)
        return callers_list, error_str

    t0 = time.time()
    target_func_code, target_source_file = find_func_source_code(target_func_name, _FUNCTION_DATA_CACHE)
    t_staged += _record_timing(target_func_name, "source_lookup", time.time() - t0)

    # Default conditionality fields (initialized early so error paths can use them)
    conditionality = "unconditional"
    must_check = False
    retry_on_failure = False
    retry_reason = ""
    contract_summary = ""

    source_valid, source_check_reason = _verify_source_contains_function(target_func_name, target_func_code)
    if not source_valid:
        print(f"[{target_func_name}] Source code mismatch ({source_check_reason}). Skipping.")
        error_str = f"source_code_mismatch: {source_check_reason}"
        final_payload = {
            "status": "incomplete",
            "reason": error_str,
            "is_wrapper": False,
            "functionality_list": [],
            "callee_count": len(callee_get_put_func_info_list)
        }
        finalize_wrapper_trace(FunctionResult_dir, target_func_name, final_payload)
        save_functionality_to_db(target_func_name, [], callee_get_put_func_info_list, False,
                                 "not_in_db", FunctionResult_dir, stages=stages, final=final_payload,
                                 conditionality=conditionality, must_check=must_check,
                                 retry_on_failure=retry_on_failure, retry_reason=retry_reason,
                                 contract_summary=contract_summary)
        t_total = time.time() - t_func_start
        _record_timing(target_func_name, "overhead", t_total - t_staged)
        return callers_list, error_str

    callee_get_put_func_info = format_callee_get_put_func_info(callee_get_put_func_info_list)

    # --- LLM Pipeline (retry up to 3 times on failure) ---
    MAX_RETRIES = 3
    functionality_list = []
    should_continue = False
    end_flag = False
    purity = None
    pipeline_ok = False

    for attempt in range(1, MAX_RETRIES + 1):
        stages = {}
        if attempt > 1:
            print(f"[{target_func_name}] Retry attempt {attempt}/{MAX_RETRIES}...")

        try:
            # --- Stage: Judge ---
            t0 = time.time()
            wrapper_judgment_result = run_wrapper_judge(
                api_key, api_url, model, target_func_name, target_func_code, callee_get_put_func_info
            )
            t_staged += _record_timing(target_func_name, "judge", time.time() - t0)
            update_wrapper_stage_trace(FunctionResult_dir, target_func_name, "judge", wrapper_judgment_result)
            wrapper_judgment = wrapper_judgment_result.get("parsed", {})
            stages["judge"] = wrapper_judgment
            end_flag = bool(wrapper_judgment.get("is_wrapper", False))
            purity = wrapper_judgment.get("purity")
            functionality_list = []
            # Stage 4 (Expand) removed — caller lookup is now directly driven by is_wrapper:
            #   is_wrapper=true  → ALWAYS check callers (should_continue=true)
            #   is_wrapper=false → NEVER check callers (should_continue=false)
            should_continue = end_flag
            # Extract conditionality fields from judge for per-operation retry decisions
            conditionality = wrapper_judgment.get("conditionality", "unconditional")
            must_check = bool(wrapper_judgment.get("must_check", False))
            retry_on_failure = bool(wrapper_judgment.get("retry_on_failure", False))
            retry_reason = wrapper_judgment.get("retry_reason", "")
            contract_summary = wrapper_judgment.get("contract_summary", "")

            if end_flag:
                # --- Stage: Extract ---
                # 优先 DWARF 枚举 (87% 成功率), 失败回退 LLM
                extract_result = None
                candidate_result_list = []
                extract_source = "llm"
                t0 = time.time()

                if HAS_DWARF and callee_get_put_func_info_list:
                    try:
                        dwarf_result = dwarf_extract(
                            caller_func_name=target_func_name,
                            caller_func_code=target_func_code,
                            callee_info_list=callee_get_put_func_info_list,
                            function_result_dir=FunctionResult_dir,
                        )
                        if dwarf_result.get("success"):
                            if dwarf_result.get("functionality_list"):
                                candidate_result_list = dwarf_result["functionality_list"]
                                extract_source = dwarf_result.get("source", "dwarf_enumerated")
                            elif dwarf_result.get("need_llm_judge"):
                                # 多条候选链 → 交给 LLM Judge 判断
                                extract_source = "dwarf_multi_chain"
                                candidate_result_list = []  # LLM 还未介入
                                stages["extract"] = {
                                    "source": extract_source,
                                    "confidence": "low",
                                    "candidates_for_llm": dwarf_result["need_llm_judge"],
                                }
                                print(f"    [{target_func_name}] DWARF: multi-chain, need LLM ({len(dwarf_result['need_llm_judge'])} candidates)")
                            if candidate_result_list:
                                stages["extract"] = {
                                    "source": extract_source,
                                    "confidence": dwarf_result.get("confidence", "medium"),
                                    "ResultList": candidate_result_list,
                                }
                                print(f"    [{target_func_name}] DWARF: "
                                      f"confidence={dwarf_result['confidence']}, "
                                      f"chains={len(candidate_result_list)}")
                    except Exception as exc:
                        print(f"    [{target_func_name}] DWARF failed: {exc}")

                if not candidate_result_list:
                    extract_result = run_path_extract_iterative(
                        api_key, api_url, model, target_func_name, target_func_code, callee_get_put_func_info
                    )
                    t_staged += _record_timing(target_func_name, "extract", time.time() - t0)
                    update_wrapper_stage_trace(FunctionResult_dir, target_func_name, "extract", extract_result)
                    stages["extract"] = extract_result.get("parsed", {})
                    candidate_result_list = extract_result.get("parsed", {}).get("ResultList", [])
                else:
                    t_staged += _record_timing(target_func_name, "extract_dwarf", time.time() - t0)
                    update_wrapper_stage_trace(FunctionResult_dir, target_func_name, "extract", stages.get("extract", {}))

                # --- Stage: Check ---
                t0 = time.time()
                check_result = run_consistency_check(
                    api_key, api_url, model, target_func_name, target_func_code,
                    callee_get_put_func_info, candidate_result_list,
                )
                t_staged += _record_timing(target_func_name, "check", time.time() - t0)
                update_wrapper_stage_trace(FunctionResult_dir, target_func_name, "check", check_result)
                stages["check"] = check_result.get("parsed", {})
                functionality_list = check_result.get("parsed", {}).get("ResultList", [])

                # --- Stage: Re-evaluate (conditional) ---
                if not functionality_list and candidate_result_list:
                    print(f"[{target_func_name}] Conflict: extract found {len(candidate_result_list)} ops "
                          f"but check cleared them. Re-evaluating.")
                    check_reason = check_result.get("parsed", {}).get("reason", "no reason given")
                    try:
                        t0 = time.time()
                        reeval_result = run_conflict_resolution(
                            api_key, api_url, model, target_func_name, target_func_code,
                            callee_get_put_func_info, candidate_result_list, check_reason
                        )
                        t_staged += _record_timing(target_func_name, "reevaluate", time.time() - t0)
                        update_wrapper_stage_trace(FunctionResult_dir, target_func_name,
                                                   "reevaluate", reeval_result)
                        reeval_parsed = reeval_result.get("parsed", {})
                        stages["reevaluate"] = reeval_parsed
                        if not reeval_parsed.get("is_wrapper", True):
                            end_flag = False
                            should_continue = False  # sync with overturned wrapper judgment
                            functionality_list = []
                            purity = reeval_parsed.get("purity", purity)
                            print(f"  -> re-evaluation: {target_func_name} is NOT a wrapper")
                        else:
                            functionality_list = reeval_parsed.get("ResultList", [])
                            purity = reeval_parsed.get("purity", purity)
                            should_continue = True  # re-evaluation confirmed wrapper
                            print(f"  -> re-evaluation: restored {len(functionality_list)} ops")
                    except Exception as exc:
                        print(f"[{target_func_name}] Re-evaluation error: {exc}")

            pipeline_ok = True
            break  # success — exit retry loop

        except Exception as exc:
            print(f"[{target_func_name}] Attempt {attempt}/{MAX_RETRIES} failed: {exc}")
            if attempt >= MAX_RETRIES:
                error_str = f"pipeline_failed_after_{MAX_RETRIES}_attempts: {exc}"
                final_payload = {
                    "status": "error", "stage": "pipeline",
                    "reason": str(exc), "attempts": attempt,
                    "is_wrapper": end_flag
                }
                finalize_wrapper_trace(FunctionResult_dir, target_func_name, final_payload)
                save_functionality_to_db(target_func_name, functionality_list, callee_get_put_func_info_list,
                                         end_flag, is_update, FunctionResult_dir,
                                         purity=purity, stages=stages, final=final_payload,
                                         conditionality=conditionality, must_check=must_check,
                                         retry_on_failure=retry_on_failure, retry_reason=retry_reason,
                                 contract_summary=contract_summary)
                t_total = time.time() - t_func_start
                _record_timing(target_func_name, "overhead", t_total - t_staged)
                return callers_list, error_str

    if not pipeline_ok:
        # Should not be reachable, but guard against it
        error_str = "pipeline_exited_retry_loop_without_success"
        final_payload = {"status": "error", "reason": error_str}
        finalize_wrapper_trace(FunctionResult_dir, target_func_name, final_payload)
        save_functionality_to_db(target_func_name, [], callee_get_put_func_info_list, False,
                                 "not_in_db", FunctionResult_dir, stages=stages, final=final_payload,
                                 conditionality=conditionality, must_check=must_check,
                                 retry_on_failure=retry_on_failure, retry_reason=retry_reason,
                                 contract_summary=contract_summary)
        t_total = time.time() - t_func_start
        _record_timing(target_func_name, "overhead", t_total - t_staged)
        return callers_list, error_str

    # --- I/O: save results ---
    t_io_start = time.time()
    final_payload = {
        "status": "ok",
        "is_wrapper": end_flag,
        "purity": purity,
        "functionality_list": functionality_list,
        "callee_count": len(callee_get_put_func_info_list),
        "conditionality": conditionality,
        "must_check": must_check,
        "retry_on_failure": retry_on_failure,
        "retry_reason": retry_reason,
        "contract_summary": contract_summary,
    }
    save_functionality_to_db(target_func_name, functionality_list, callee_get_put_func_info_list,
                             end_flag, is_update, FunctionResult_dir,
                             purity=purity,
                             stages=stages, final=final_payload,
                             conditionality=conditionality, must_check=must_check,
                             retry_on_failure=retry_on_failure, retry_reason=retry_reason,
                             contract_summary=contract_summary)
    finalize_wrapper_trace(FunctionResult_dir, target_func_name, final_payload)
    t_staged += _record_timing(target_func_name, "io_save", time.time() - t_io_start)

    # --- Stage: Callers ---
    # is_wrapper=true → always check callers; is_wrapper=false → never check callers
    if end_flag:
        t0 = time.time()
        target_func_info_list = get_callers(target_func_name, linux_dir)
        t_staged += _record_timing(target_func_name, "callers", time.time() - t0)
        for target_func_info in target_func_info_list:
            caller_func_name = target_func_info["caller"]
            callers_list.append(caller_func_name)
            print(f"[{target_func_name}] -> caller: {caller_func_name}")
            if functionality_list:
                save_callee_to_db(caller_func_name, functionality_list, target_func_name,
                                 FunctionResult_dir,
                                 contract_summary=contract_summary,
                                 conditionality=conditionality,
                                 must_check=must_check,
                                 retry_on_failure=retry_on_failure)

    t_total = time.time() - t_func_start
    _record_timing(target_func_name, "overhead", max(0, t_total - t_staged))
    return callers_list, error_str


def _recover_queue_from_checkpoint(init_target_func_name_list, FunctionResult_dir, linux_dir):
    """断点续跑：扫描已有结果目录，模拟 BFS 遍历恢复处理队列。

    遍历策略与原逻辑一致：
      1. 扫描 FunctionResult_dir 下所有 {func}.json，识别已完成分析（含 end_flag）的函数
      2. 从种子函数列表出发，BFS 遍历已完成的 wrapper 函数的 callers，
         将尚未完成的函数加入队列
      3. 已完成的函数放入 in_flight 以防止重复入队

    Returns:
        (queue, in_flight, func_count, error_queue, error_funcs_to_retry)
    """
    from collections import deque

    completed: dict = {}    # func_name -> is_wrapper (bool)
    error_funcs: list = []  # 分析过但状态非 ok 的函数

    if not os.path.isdir(FunctionResult_dir):
        return deque(init_target_func_name_list), set(init_target_func_name_list), 0, [], []

    # ── 第一遍扫描：识别所有已完成函数 ──
    for fname in os.listdir(FunctionResult_dir):
        if not fname.endswith(".json") or fname == WRAPPER_TRACE_FILENAME:
            continue
        func_name = fname[:-5]  # 去掉 .json
        db_path = os.path.join(FunctionResult_dir, fname)
        try:
            with open(db_path, "r") as f:
                entry = json.load(f)
        except (IOError, json.JSONDecodeError):
            continue

        if "end_flag" in entry:
            completed[func_name] = entry.get("end_flag", False)
            status = entry.get("final", {}).get("status", "ok")
            if status != "ok":
                error_funcs.append(func_name)

    if not completed:
        print("[Resume] No completed functions found — starting fresh.")
        return deque(init_target_func_name_list), set(init_target_func_name_list), 0, [], []

    print(f"[Resume] Found {len(completed)} completed function(s) in {FunctionResult_dir}")
    if error_funcs:
        print(f"[Resume] {len(error_funcs)} function(s) with error status will be retried")

    # ── 第二遍：BFS 模拟遍历，恢复队列 ──
    queue = deque()
    in_flight = set(completed.keys())  # 已完成的函数阻止重复入队
    visited: set = set()

    bfs_queue = deque(init_target_func_name_list)
    for fn in init_target_func_name_list:
        visited.add(fn)
        if fn not in completed:
            queue.append(fn)
            in_flight.add(fn)

    caller_discovery_count = 0
    while bfs_queue:
        fn = bfs_queue.popleft()
        # 只有「已完成且是 wrapper」的函数才需要重新发现其 callers
        if completed.get(fn, False):
            try:
                caller_info_list = get_callers(fn, linux_dir)
                caller_discovery_count += 1
            except Exception as exc:
                print(f"[Resume] Warning: get_callers({fn}) failed: {exc}")
                continue
            for info in caller_info_list:
                caller = info["caller"]
                if caller not in visited:
                    visited.add(caller)
                    bfs_queue.append(caller)
                    if caller not in completed:
                        queue.append(caller)
                        in_flight.add(caller)

    print(f"[Resume] BFS recovered {caller_discovery_count} wrapper(s) re-scanned, "
          f"{len(queue)} function(s) pending, {len(completed)} already done")

    # ── 错误函数重新加入队列（如果不在 in_flight 中）──
    retry_count = 0
    for ef in error_funcs:
        if ef not in in_flight:
            queue.append(ef)
            in_flight.add(ef)
            retry_count += 1
    if retry_count:
        print(f"[Resume] {retry_count} error function(s) re-queued for retry")

    return queue, in_flight, len(completed), error_funcs, []


def cf_chat_init(init_target_func_name_list, DataShare_dir, proj_name, api_key, api_url, location_info_dir, model="gpt-5", linux_dir=None, use_ctags_fallback=False):

    FunctionResult_dir = os.path.join(DataShare_dir, "FunctionResult", proj_name)
    os.makedirs(FunctionResult_dir, exist_ok=True)

    global _FUNCTION_DATA_CACHE, _FUNC_LOCATOR, _USE_CTAGS_FALLBACK
    _USE_CTAGS_FALLBACK = use_ctags_fallback

    # initialize AccurateFuncLocator (cscope-based, primary lookup strategy)
    if linux_dir:
        cscope_path = os.path.join(linux_dir, "cscope.out")
        if os.path.exists(cscope_path):
            _FUNC_LOCATOR = AccurateFuncLocator(linux_dir)
            print("AccurateFuncLocator initialized (cscope-based).")
        elif not use_ctags_fallback:
            raise RuntimeError(
                f"cscope database not found at {cscope_path}. "
                f"Run 'make cscope' in the kernel source directory first, "
                f"or set use_ctags_fallback=True to use the ctags-based method."
            )
        else:
            print("Warning: cscope database not found; falling back to ctags-based lookup.")
    else:
        print("WARNING: linux_dir is empty — caller lookup (cscope) will return no results. "
              "Set linux_dir to a kernel source tree with cscope.out to enable caller discovery.")

    # optionally load ctags-based cache as fallback
    if _USE_CTAGS_FALLBACK:
        print("Loading ctags-based func_loc.json (fallback enabled)...")
        with open(os.path.join(location_info_dir, "func_loc.json"), "r") as fp:
            _FUNCTION_DATA_CACHE = json.load(fp)
    else:
        _FUNCTION_DATA_CACHE = {"functions": {}}
        print("ctags fallback disabled — using cscope-only mode.")

    # 初始化 trace 内存缓存（只读磁盘一次）
    _init_trace_cache(FunctionResult_dir)

    t_pipeline_start = time.time()
    # 队列上限警告阈值（超过此值说明可能陷入循环依赖）
    _MAX_QUEUE_WARN = 25000
    # 定期进度报告间隔（每 N 个函数输出一次中间统计）
    _PROGRESS_INTERVAL = 128
    _last_progress_time = t_pipeline_start

    # ── 断点续跑：检测目标目录是否非空，若是则恢复队列 ──
    from collections import deque
    existing_files = [f for f in os.listdir(FunctionResult_dir)
                      if f.endswith(".json") and f != WRAPPER_TRACE_FILENAME]
    if existing_files and linux_dir:
        print(f"\n{'=' * 65}")
        print(f"[Resume] Target directory non-empty ({len(existing_files)} .json files).")
        print(f"[Resume] Entering checkpoint recovery mode...")
        print(f"{'=' * 65}")
        queue, in_flight, func_count, error_queue, _ = _recover_queue_from_checkpoint(
            init_target_func_name_list, FunctionResult_dir, linux_dir
        )
        print(f"[Resume] Recovery complete. Starting/continuing pipeline...\n")
    else:
        if existing_files and not linux_dir:
            print("[Resume] WARNING: Target directory non-empty but linux_dir is None — "
                  "cannot recover callers. Starting fresh.")
        queue = deque(init_target_func_name_list)
        in_flight: set = set(queue)          # 队列中 + 运行中
        func_count = 0
        error_queue: list = []

    # ── 共享线程池 + FIFO 队列 ──
    # 所有函数共享一个 ThreadPoolExecutor；caller 发现后追加到队列尾部，
    # 队列头部有空位时立即取出提交。FIFO 保证先发现的先跑（≈BFS），
    # 同时不同深度的函数可自然重叠，无需等待整层完成。
    pending_resubmit: set = set()        # 运行中被新增 callee，完成后重新入队
    _qlock = threading.Lock()

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        pending: dict = {}  # Future -> function_name

        def _enqueue(fn_name):
            """追加到队列尾部。若已在 in_flight 则标记待重提交。"""
            with _qlock:
                if fn_name in in_flight:
                    pending_resubmit.add(fn_name)
                    return False
                in_flight.add(fn_name)
                queue.append(fn_name)
                return True

        def _submit_from_queue():
            """从队列头部取出函数提交到线程池，直到满员或队列空。"""
            while len(pending) < _MAX_WORKERS and queue:
                fn = queue.popleft()
                f = executor.submit(
                    _analyze_single_function, fn,
                    api_key, api_url, model, linux_dir, FunctionResult_dir,
                    queue_remain=len(queue)
                )
                pending[f] = fn

        # 初始提交（队列头部 = 种子函数）
        _submit_from_queue()

        while pending:
            for future in as_completed(list(pending.keys())):
                fn_name = pending.pop(future)
                try:
                    callers, err = future.result()
                except Exception as exc:
                    print(f"[{fn_name}] Future exception: {exc}")
                    error_queue.append(fn_name)
                    callers, err = [], str(exc)

                func_count += 1

                if err:
                    error_queue.append(fn_name)

                # ── 重提交检查 ──
                with _qlock:
                    in_flight.discard(fn_name)
                    needs_resubmit = fn_name in pending_resubmit
                    if needs_resubmit:
                        pending_resubmit.discard(fn_name)

                if needs_resubmit:
                    _enqueue(fn_name)

                # ── caller 追加到队列尾部（FIFO = 先发现先跑）──
                if callers:
                    print(f"  [{fn_name}] -> {len(callers)} caller(s)")

                for sc in callers:
                    _enqueue(sc)

                # ── 从队列头部补充提交 ──
                _submit_from_queue()

                # ── 定期进度报告 ──
                if func_count % _PROGRESS_INTERVAL == 0:
                    checkpoint_elapsed = time.time() - t_pipeline_start
                    print(f"\n{'=' * 65}")
                    print(f"CHECKPOINT — {func_count} functions processed, "
                          f"elapsed={checkpoint_elapsed:.1f}s ({checkpoint_elapsed/60:.1f}min), "
                          f"queue={len(queue)}, pending={len(pending)}, "
                          f"errors_so_far={len(error_queue)}")
                    if error_queue:
                        print(f"  Recent errors (last 10): {error_queue[-10:]}")
                    print(f"{'=' * 65}")
                    _print_timing_summary_partial(checkpoint_elapsed)
                    _last_progress_time = time.time()

                # ── 队列膨胀保护 ──
                if len(queue) > _MAX_QUEUE_WARN:
                    print(f"WARNING: queue size={len(queue)} exceeds {_MAX_QUEUE_WARN}. "
                          f"Deduplicating...")
                    seen = set()
                    deduped = deque()
                    for name in queue:
                        if name not in seen:
                            seen.add(name)
                            deduped.append(name)
                    removed = len(queue) - len(deduped)
                    queue = deduped
                    print(f"  Removed {removed} duplicates. Queue size now: {len(queue)}")

    t_total = time.time() - t_pipeline_start

    _flush_trace_cache(FunctionResult_dir)

    print(f"\nDetection completed. {func_count} functions processed in {t_total:.1f}s. "
          f"Errors: {len(error_queue)}")
    if error_queue:
        print(f"  Error functions: {error_queue}")
    if func_count > 0:
        _print_timing_summary(wall_clock_seconds=t_total)


# 使用示例
if __name__ == "__main__":
    api_key = os.environ.get("REFCOUNT_API_KEY", "")
    api_url = os.environ.get("REFCOUNT_API_URL", "https://api.deepseek.com")
    proj_name = os.environ.get("REFCOUNT_PROJECT_NAME", "refcount-run")
    DataShare_dir = os.environ.get("REFCOUNT_DATA_DIR", "./data")
    model = os.environ.get("REFCOUNT_MODEL", "deepseek-v4-flash")
    linux_dir = os.environ.get("REFCOUNT_KERNEL_DIR", "")
    location_info_dir = os.environ.get("REFCOUNT_TARGET_INFO_DIR", "")

    if not api_key:
        print("ERROR: REFCOUNT_API_KEY environment variable is required.")
        print("  export REFCOUNT_API_KEY=sk-xxxx")
        sys.exit(1)
    if not linux_dir:
        print("ERROR: REFCOUNT_KERNEL_DIR environment variable is required.")
        print("  export REFCOUNT_KERNEL_DIR=/path/to/linux-kernel")
        sys.exit(1)

    init_target_func_name_list = [
                                  "refcount_set",
                                  "refcount_set_release",
                                  "refcount_add_not_zero",
                                  "refcount_add_not_zero_acquire",
                                  "refcount_add",
                                  "refcount_inc_not_zero",
                                  "refcount_inc_not_zero_acquire",
                                  "refcount_inc",
                                  "refcount_dec",
                                  "refcount_dec_and_test",
                                  "refcount_dec_if_one",
                                  "refcount_dec_not_one",
                                  "refcount_dec_and_mutex_lock",
                                  "refcount_dec_and_lock",
                                  "refcount_dec_and_lock_irqsave",
                                  "kref_init",
                                  "kref_get",
                                  "kref_put",
                                  "kref_put_mutex",
                                  "kref_put_lock",
                                  "kref_get_unless_zero",
                                  ]

    cf_chat_init(init_target_func_name_list, DataShare_dir, proj_name, api_key, api_url, location_info_dir, model, linux_dir)