/*
 * Copyright (C) 2021 Oracle.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, see http://www.gnu.org/copyleft/gpl.txt
 */

#include "smatch.h"
#include "smatch_extra.h"
#include "smatch_slist.h"
#include <stdlib.h>

static int my_id;

#define REFCOUNT_FN_INC_PREFIX "__fn_trace_inc_"
#define REFCOUNT_FN_DEC_PREFIX "__fn_trace_dec_"

/*
 * Marker embedded in the smatch_state->name value so that the merge hook
 * can distinguish trace states (->name starts with this marker) from
 * ordinary inc/dec/balanced states.
 */
#define TRACE_VALUE_MARKER "@TRACE@"

/* forward declarations for net-count helpers (used by merge hook below) */
#define MAX_COMPOSITE_COUNTS 10
static bool is_any_count_state(struct smatch_state *s);
static void parse_count_state(struct smatch_state *s,
			      int **counts_out, int *n_out);
static struct smatch_state *build_count_state(int *counts, int n);
static void union_counts(int *a1, int n1, int *a2, int n2,
			 int **out, int *out_n);

/*
 * Custom merge for refcount function-trace states.
 * Instead of returning &merged when two path's function lists differ,
 * union the comma-separated lists so that inc:[...] dec:[...] displays
 * the complete set of functions across all merged paths.
 */
static struct smatch_state *refcount_trace_merge(struct smatch_state *s1,
						  struct smatch_state *s2)
{
	const char *name1, *name2;
	bool is_trace1, is_trace2;
	char buf[1024];
	char *out;
	int len;

	if (!s1)
		return s2;
	if (!s2)
		return s1;

	name1 = s1->name ? s1->name : "";
	name2 = s2->name ? s2->name : "";

	is_trace1 = (strncmp(name1, TRACE_VALUE_MARKER, sizeof(TRACE_VALUE_MARKER) - 1) == 0);
	is_trace2 = (strncmp(name2, TRACE_VALUE_MARKER, sizeof(TRACE_VALUE_MARKER) - 1) == 0);

	/* not a trace state — check for count states first */
	if (!is_trace1 && !is_trace2) {
		bool cnt1 = is_any_count_state(s1);
		bool cnt2 = is_any_count_state(s2);

		if (cnt1 || cnt2) {
			/* one side not a count state -> keep the count side */
			if (!cnt1)
				return s2;
			if (!cnt2)
				return s1;

			/* both are count states — union the count sets */
			{
				int *c1, n1, *c2, n2;
				int *combined, combined_n;
				struct smatch_state *result;

				parse_count_state(s1, &c1, &n1);
				parse_count_state(s2, &c2, &n2);
				union_counts(c1, n1, c2, n2,
					     &combined, &combined_n);
				result = build_count_state(combined, combined_n);
				free(c1);
				free(c2);
				free(combined);
				return result;
			}
		}

		/* fall back to default string merge */
		return merge_str_state(s1, s2);
	}

	/*
	 * One side is a trace state, the other is undefined/empty/etc.
	 * This happens when one path had a refcount call and the other
	 * didn't.  Keep only the trace state's list.
	 */
	if (!is_trace1)
		return s2;
	if (!is_trace2)
		return s1;

	/* same string — no merge needed */
	if (strcmp(name1, name2) == 0)
		return s1;

	/* one or both is "merged" — keep the other if possible */
	if (strcmp(name1, "merged") == 0)
		return s2;
	if (strcmp(name2, "merged") == 0)
		return s1;

	/* strip markers to get the actual function list */
	if (is_trace1)
		name1 += sizeof(TRACE_VALUE_MARKER) - 1;
	if (is_trace2)
		name2 += sizeof(TRACE_VALUE_MARKER) - 1;

	/* both empty → empty */
	if (!name1[0] && !name2[0])
		return alloc_state_str(alloc_string(TRACE_VALUE_MARKER));

	/*
	 * Union the comma-separated function lists.
	 * Build the result by copying from s1 first, then appending
	 * items from s2 that are not already in s1.
	 */
	snprintf(buf, sizeof(buf), "%s", name1);
	out = buf + strlen(buf);
	len = buf + sizeof(buf) - out;

	if (name2[0]) {
		char tmp[1024];
		char *token, *save;

		snprintf(tmp, sizeof(tmp), "%s", name2);
		for (token = strtok_r(tmp, ",", &save); token;
		     token = strtok_r(NULL, ",", &save)) {
			/* Check if token already in buf (simple strstr dedup) */
			char *found = buf;
			while ((found = strstr(found, token))) {
				char before = (found == buf) ? ',' : *(found - 1);
				char after = found[strlen(token)];
				if ((before == ',' || found == buf) &&
				    (after == '\0' || after == ','))
					break;
				found++;
			}
			if (!found && len > 1) {
				int n = snprintf(out, len, ",%s", token);
				if (n > 0) {
					out += n;
					len -= n;
				}
			}
		}
	}

	/* put the marker back on the result */
	{
		char result[1024];
		snprintf(result, sizeof(result), "%s%s", TRACE_VALUE_MARKER, buf);
		return alloc_state_str(alloc_string(result));
	}
}

/* strip the TRACE_VALUE_MARKER prefix from a function list string */
static const char *strip_trace_marker(const char *s)
{
	if (s && strncmp(s, TRACE_VALUE_MARKER, sizeof(TRACE_VALUE_MARKER) - 1) == 0)
		return s + sizeof(TRACE_VALUE_MARKER) - 1;
	return s;
}

/* ---------- net-count state helpers ---------- */

/*
 * is_single_count_state: true for alloc_state_num-created states.
 * We check the name (decimal integer) rather than .data because
 * alloc_state_num(0) stores INT_PTR(0) == NULL in the data field.
 */
static bool is_single_count_state(struct smatch_state *s)
{
	const char *p;

	if (!s || !s->name || !s->name[0])
		return false;

	/* trace states carry @TRACE@ in the name */
	if (strncmp(s->name, TRACE_VALUE_MARKER,
		    sizeof(TRACE_VALUE_MARKER) - 1) == 0)
		return false;

	/* composite states start with "rcset:" */
	if (strncmp(s->name, "rcset:", 6) == 0)
		return false;

	/*
	 * Single-count states are decimal integers (possibly negative).
	 * Check that the entire name parses as an integer.
	 */
	p = s->name;
	if (*p == '-')
		p++;
	if (!*p)
		return false;	/* just "-" is not a number */
	while (*p) {
		if (*p < '0' || *p > '9')
			return false;
		p++;
	}
	return true;
}

/* Get the net count from a single-count state (parses the name). */
static int single_count_value(struct smatch_state *s)
{
	if (!s || !s->name)
		return 0;
	return atoi(s->name);
}

/*
 * is_composite_count_state: true when name starts with "rcset:".
 */
static bool is_composite_count_state(struct smatch_state *s)
{
	return s && s->name && strncmp(s->name, "rcset:", 6) == 0;
}

static bool is_any_count_state(struct smatch_state *s)
{
	return is_single_count_state(s) || is_composite_count_state(s);
}

/*
 * parse_count_state: extract all net-count integers from a state.
 *   single-count state  -> 1-element array {n}
 *   composite "rcset:"  -> parsed sorted CSV integers
 *   anything else       -> 0 entries
 * Caller must free *counts_out.
 */
static void parse_count_state(struct smatch_state *s,
			      int **counts_out, int *n_out)
{
	*counts_out = NULL;
	*n_out = 0;

	if (!s)
		return;

	if (is_single_count_state(s)) {
		*counts_out = malloc(sizeof(int));
		if (!*counts_out)
			return;
		(*counts_out)[0] = single_count_value(s);
		*n_out = 1;
		return;
	}

	if (is_composite_count_state(s)) {
		const char *p = s->name + 6;	/* skip "rcset:" */
		char *buf, *tok, *save;
		int cap, *arr, n;

		buf = strdup(p);
		if (!buf)
			return;
		cap = 4;
		arr = malloc(cap * sizeof(int));
		if (!arr) {
			free(buf);
			return;
		}
		n = 0;
		for (tok = strtok_r(buf, ",", &save); tok;
		     tok = strtok_r(NULL, ",", &save)) {
			if (n >= cap) {
				cap *= 2;
				arr = realloc(arr, cap * sizeof(int));
				if (!arr) {
					free(buf);
					return;
				}
			}
			arr[n++] = atoi(tok);
		}
		free(buf);
		*counts_out = arr;
		*n_out = n;
	}
}

/*
 * add_unique_count: insert cnt into a sorted-dedup'd array.
 * Returns new length.  Caller ensures arr has capacity.
 */
static int add_unique_count(int *arr, int n, int cnt)
{
	int i;

	for (i = 0; i < n; i++) {
		if (arr[i] == cnt)
			return n;		/* duplicate */
		if (arr[i] > cnt) {
			memmove(arr + i + 1, arr + i,
				(n - i) * sizeof(int));
			arr[i] = cnt;
			return n + 1;
		}
	}
	arr[n] = cnt;
	return n + 1;
}

/*
 * build_count_state: produce a smatch_state from a set of net counts.
 *   single count  -> alloc_state_num(n)
 *   multiple      -> alloc_state_str("rcset:N1,N2,...")   (sorted)
 *   overflow      -> alloc_state_str("rcset:overflow")
 *   empty         -> returns NULL
 */
static struct smatch_state *build_count_state(int *counts, int n)
{
	char buf[512];
	char *p;
	int i, remain;

	if (n <= 0)
		return NULL;

	if (n > MAX_COMPOSITE_COUNTS)
		return alloc_state_str(alloc_string("rcset:overflow"));

	if (n == 1)
		return alloc_state_num(counts[0]);

	p = buf;
	remain = sizeof(buf);
	for (i = 0; i < n; i++) {
		int w;

		if (i == 0)
			w = snprintf(p, remain, "rcset:%d", counts[i]);
		else
			w = snprintf(p, remain, ",%d", counts[i]);
		if (w < 0 || w >= remain)
			return alloc_state_str(alloc_string("rcset:overflow"));
		p += w;
		remain -= w;
	}
	return alloc_state_str(alloc_string(buf));
}

/*
 * union_counts: merge two sorted-dedup'd count arrays.
 * Result is sorted-dedup'd.  Caller frees *out.
 */
static void union_counts(int *a1, int n1, int *a2, int n2,
			 int **out, int *out_n)
{
	int cap = n1 + n2 + 4;
	int *arr;
	int n, i;

	arr = malloc(cap * sizeof(int));
	if (!arr) {
		*out = NULL;
		*out_n = 0;
		return;
	}
	n = 0;
	for (i = 0; i < n1; i++)
		n = add_unique_count(arr, n, a1[i]);
	for (i = 0; i < n2; i++)
		n = add_unique_count(arr, n, a2[i]);
	*out = arr;
	*out_n = n;
}

/*
 * apply_delta: adjust every possible net-count in state s by delta,
 * return the resulting state.
 *
 * Handles NULL, &undefined, single-count, composite ("rcset:"), and
 * &merged (by iterating sm->possible).
 */
static struct smatch_state *apply_delta(struct smatch_state *s,
					struct sm_state *sm, int delta)
{
	int *counts = NULL, n = 0;
	int *new_arr = NULL;
	int new_n = 0, new_cap = 0;
	struct sm_state *tmp;
	int i;

	/* --- no existing state -> start from 0 ---------------- */
	if (!s || s == &undefined)
		return alloc_state_num(delta);

	/* --- composite state ---------------------------------- */
	if (is_composite_count_state(s)) {
		parse_count_state(s, &counts, &n);
		goto apply;
	}

	/* --- single-count state ------------------------------ */
	if (is_single_count_state(s))
		return alloc_state_num(single_count_value(s) + delta);

	/* --- &merged -> iterate possible list ----------------- */
	if (s == &merged && sm) {
		new_n = 0;
		new_cap = 8;
		new_arr = malloc(new_cap * sizeof(int));
		if (!new_arr)
			return alloc_state_num(delta);

		FOR_EACH_PTR(sm->possible, tmp) {
			int *sub, sub_n, j;

			parse_count_state(tmp->state, &sub, &sub_n);
			if (sub_n == 0)
				continue;
			for (j = 0; j < sub_n; j++) {
				if (new_n >= new_cap) {
					new_cap *= 2;
					new_arr = realloc(new_arr,
							  new_cap * sizeof(int));
					if (!new_arr)
						goto done;
				}
				new_n = add_unique_count(new_arr, new_n,
							 sub[j] + delta);
			}
			free(sub);
		} END_FOR_EACH_PTR(tmp);
		goto done;
	}

	/* --- &merged without sm, or unrecognized -> fresh ----- */
	return alloc_state_num(delta);

apply:
	new_n = 0;
	new_cap = n + 4;
	new_arr = malloc(new_cap * sizeof(int));
	if (!new_arr)
		return alloc_state_num(delta);

	for (i = 0; i < n; i++) {
		if (new_n >= new_cap) {
			new_cap *= 2;
			new_arr = realloc(new_arr, new_cap * sizeof(int));
			if (!new_arr)
				goto done;
		}
		new_n = add_unique_count(new_arr, new_n,
					 counts[i] + delta);
	}
	free(counts);

done:
	{
		struct smatch_state *result;

		result = new_n ? build_count_state(new_arr, new_n)
			       : alloc_state_num(delta);
		free(new_arr);
		return result;
	}
}

/* ---------- refcount function name tracking ---------- */

static const char *get_call_fn_name(struct expression *expr)
{
	struct expression *call = expr;

	while (call && call->type == EXPR_ASSIGNMENT)
		call = strip_expr(call->right);
	if (!call || call->type != EXPR_CALL)
		return NULL;
	if (call->fn->type != EXPR_SYMBOL)
		return NULL;
	return expr_to_str(call->fn);
}

/*
 * Accumulate refcount function calls: append instead of overwrite,
 * so every get/put function on a path is recorded.
 * inc and dec are tracked in separate comma-separated lists.
 */
static void record_refcount_fn_call(const char *name, struct symbol *sym,
				    const char *fn_name, const char *direction)
{
	char buf[256];
	char new_data[512];
	struct smatch_state *old_state;
	const char *prefix;
	const char *old_val;  /* value without marker */

	prefix = (strcmp(direction, "inc") == 0)
		? REFCOUNT_FN_INC_PREFIX : REFCOUNT_FN_DEC_PREFIX;

	snprintf(buf, sizeof(buf), "%s%s", prefix, name);
	old_state = get_state(my_id, buf, sym);

	old_val = strip_trace_marker(old_state ? old_state->name : NULL);

	if (old_state && old_val && old_val[0] &&
	    strcmp(old_val, "merged") != 0) {
		/* append, deduplicate */
		if (strstr(old_val, fn_name) == NULL) {
			snprintf(new_data, sizeof(new_data), "%s%s,%s",
				 TRACE_VALUE_MARKER, old_val, fn_name);
			set_state(my_id, buf, sym, alloc_state_str(new_data));
		}
		/* else: already in list, skip */
	} else if (old_state && old_val && strcmp(old_val, "merged") == 0) {
		/* merged — can't track further */
		;
	} else {
		snprintf(new_data, sizeof(new_data), "%s%s",
			 TRACE_VALUE_MARKER, fn_name);
		set_state(my_id, buf, sym, alloc_state_str(new_data));
	}
}

/*
 * Retrieve the accumulated inc/dec function lists for a refcount variable.
 * Each list is a comma-separated string of function names.
 */
static void get_refcount_fn_lists(const char *name, struct symbol *sym,
				  char *inc_buf, size_t inc_size,
				  char *dec_buf, size_t dec_size)
{
	char buf[256];
	struct smatch_state *state;
	const char *val;

	snprintf(buf, sizeof(buf), "%s%s", REFCOUNT_FN_INC_PREFIX, name);
	state = get_state(my_id, buf, sym);
	val = strip_trace_marker(state ? state->name : NULL);
	if (val && val[0] && strcmp(val, "merged") != 0)
		snprintf(inc_buf, inc_size, "%s", val);
	else if (val && strcmp(val, "merged") == 0)
		snprintf(inc_buf, inc_size, "(merged)");
	else
		inc_buf[0] = '\0';

	snprintf(buf, sizeof(buf), "%s%s", REFCOUNT_FN_DEC_PREFIX, name);
	state = get_state(my_id, buf, sym);
	val = strip_trace_marker(state ? state->name : NULL);
	if (val && val[0] && strcmp(val, "merged") != 0)
		snprintf(dec_buf, dec_size, "%s", val);
	else if (val && strcmp(val, "merged") == 0)
		snprintf(dec_buf, dec_size, "(merged)");
	else
		dec_buf[0] = '\0';
}

static const char *get_refcount_fn_trace(const char *name, struct symbol *sym)
{
	static char result[512];
	char inc_buf[256], dec_buf[256];

	get_refcount_fn_lists(name, sym, inc_buf, sizeof(inc_buf),
			      dec_buf, sizeof(dec_buf));

	if (inc_buf[0] && dec_buf[0])
		snprintf(result, sizeof(result), "inc:[%s] dec:[%s]",
			 inc_buf, dec_buf);
	else if (inc_buf[0])
		snprintf(result, sizeof(result), "inc:[%s]", inc_buf);
	else if (dec_buf[0])
		snprintf(result, sizeof(result), "dec:[%s]", dec_buf);
	else
		return "(unknown refcount fn)";

	return result;
}

/* ---------- hook callbacks ---------- */

static void match_inc(struct expression *expr, const char *name, struct symbol *sym)
{
	const char *fn = get_call_fn_name(expr);
	struct sm_state *sm;
	struct smatch_state *old, *new;

	if (fn)
		record_refcount_fn_call(name, sym, fn, "inc");

	sm = get_sm_state(my_id, name, sym);
	old = sm ? sm->state : NULL;
	new = apply_delta(old, sm, +1);
	set_state(my_id, name, sym, new);
}

static void match_dec(struct expression *expr, const char *name, struct symbol *sym)
{
	const char *fn = get_call_fn_name(expr);
	struct sm_state *sm;
	struct smatch_state *old, *new;

	if (fn)
		record_refcount_fn_call(name, sym, fn, "dec");

	sm = get_sm_state(my_id, name, sym);
	old = sm ? sm->state : NULL;
	new = apply_delta(old, sm, -1);
	set_state(my_id, name, sym, new);
}

/* ---------- check functions ---------- */

/*
 * check_count: detect inconsistent refcount state across different fail paths.
 * If success paths always have net > 0, but fail paths have some net > 0
 * (missing put) and some net <= 0 (balanced or excess), that inconsistency
 * is a bug.
 */
static void check_count(const char *name, struct symbol *sym)
{
	struct stree *stree, *orig;
	struct sm_state *return_sm;
	struct range_list *dec_lines = NULL;
	struct range_list *inc_lines = NULL;
	struct sm_state *sm;
	sval_t line = sval_type_val(&int_ctype, 0);
	int success_path_increments = 0;
	int success_path_unknown = 0;

	FOR_EACH_PTR(get_all_return_strees(), stree) {
		orig = __swap_cur_stree(stree);

		if (is_impossible_path())
			goto swap_stree;

		if (parent_is_gone_var_sym(name, sym))
			goto swap_stree;

		return_sm = get_sm_state(RETURN_ID, "return_ranges", NULL);
		if (!return_sm)
			goto swap_stree;
		line.value = return_sm->line;

		sm = get_sm_state(my_id, name, sym);

		if (success_fail_return(estate_rl(return_sm->state)) == RET_SUCCESS) {
			if (sm) {
				struct sm_state *tmp;
				int min_net = INT_MAX, max_net = INT_MIN;

				FOR_EACH_PTR(sm->possible, tmp) {
					int *counts, n;

					parse_count_state(tmp->state, &counts, &n);
					for (int i = 0; i < n; i++) {
						if (counts[i] < min_net)
							min_net = counts[i];
						if (counts[i] > max_net)
							max_net = counts[i];
					}
					free(counts);
				} END_FOR_EACH_PTR(tmp);

				/* success path with consistent positive net -> increments */
				if (max_net > 0 && min_net >= 0)
					success_path_increments++;
				else
					success_path_unknown++;
			} else {
				success_path_unknown++;
			}
			goto swap_stree;
		}

		if (!sm)
			goto swap_stree;

		{
			struct sm_state *tmp;
			bool has_pos = false, has_neg_or_zero = false;

			FOR_EACH_PTR(sm->possible, tmp) {
				int *counts, n;

				parse_count_state(tmp->state, &counts, &n);
				for (int i = 0; i < n; i++) {
					if (counts[i] > 0)
						has_pos = true;
					if (counts[i] <= 0)
						has_neg_or_zero = true;
				}
				free(counts);
			} END_FOR_EACH_PTR(tmp);

			if (has_pos)
				add_range(&inc_lines, line, line);
			if (has_neg_or_zero)
				add_range(&dec_lines, line, line);
		}

	swap_stree:
		__swap_cur_stree(orig);
	} END_FOR_EACH_PTR(stree);

	if (!success_path_increments || success_path_unknown)
		return;
	if (!dec_lines || !inc_lines)
		return;

	sm_warning("inconsistent refcounting '%s' (fn: %s):",
		   name, get_refcount_fn_trace(name, sym));
	sm_printf("  inc on: %s\n", show_rl(inc_lines));
	sm_printf("  dec on: %s\n", show_rl(dec_lines));
}

/*
 * check_refcount_balance: unified per-path balance check using net-count states.
 *
 * For each return path, iterate sm->possible to find min_net / max_net:
 *   min_net >= 0 && max_net <= 0 && any_zero -> balanced
 *   max_net > 0  -> inc without dec: potential leak (missing put)
 *   min_net < 0  -> dec without inc: potential excess put
 *
 * v2 fix: trace lists (any_has_inc / any_has_dec) are now read per-return-path
 * instead of from the merged end-of-function stree.  This prevents the common
 * case where one path has inc "merged" with another path that does not,
 * causing any_has_inc/any_has_dec to become false and suppressing all warnings.
 */
static void check_refcount_balance(const char *name, struct symbol *sym)
{
	struct stree *stree, *orig;
	struct sm_state *return_sm, *sm;
	struct range_list *leak_lines = NULL;
	struct range_list *excess_put_lines = NULL;
	sval_t line = sval_type_val(&int_ctype, 0);

	/* Phase 1: per-path balance check */
	FOR_EACH_PTR(get_all_return_strees(), stree) {
		orig = __swap_cur_stree(stree);

		if (is_impossible_path())
			goto swap_stree;
		if (parent_is_gone_var_sym(name, sym))
			goto swap_stree;

		return_sm = get_sm_state(RETURN_ID, "return_ranges", NULL);
		if (!return_sm)
			goto swap_stree;
		line.value = return_sm->line;

		sm = get_sm_state(my_id, name, sym);
		if (!sm)
			goto swap_stree;

		/* Phase 1a: read per-path trace lists for any_has_inc/any_has_dec.
		 * Doing this per-return-path instead of globally prevents
		 * "merged" trace states from suppressing genuine warnings.
		 */
		char inc_fns[512] = "", dec_fns[512] = "";
		bool any_has_inc, any_has_dec;

		get_refcount_fn_lists(name, sym,
				      inc_fns, sizeof(inc_fns),
				      dec_fns, sizeof(dec_fns));
		any_has_inc = inc_fns[0] != '\0';
		any_has_dec = dec_fns[0] != '\0';

		/* iterate possible leaf/composite states to find min/max net */
		{
			struct sm_state *tmp;
			int min_net = INT_MAX, max_net = INT_MIN;
			bool any_zero = false;
			bool has_count = false;

			FOR_EACH_PTR(sm->possible, tmp) {
				int *counts, n;

				parse_count_state(tmp->state, &counts, &n);
				for (int i = 0; i < n; i++) {
					has_count = true;
					if (counts[i] < min_net)
						min_net = counts[i];
					if (counts[i] > max_net)
						max_net = counts[i];
					if (counts[i] == 0)
						any_zero = true;
				}
				free(counts);
			} END_FOR_EACH_PTR(tmp);

			if (!has_count)
				goto swap_stree;

			/* purely balanced: all sub-paths at net=0 */
			if (any_zero && min_net >= 0 && max_net <= 0) {
				sm_info("balanced refcount '%s': line=%ld inc=[%s] dec=[%s]",
					name, (long)line.value,
					inc_fns[0] ? inc_fns : "(unknown)",
					dec_fns[0] ? dec_fns : "(unknown)");
				goto swap_stree;
			}

			if (success_fail_return(estate_rl(return_sm->state)) == RET_FAIL) {
				/* Leak: some sub-path has net > 0 (more inc than dec).
				 * Only on fail paths to suppress false positives on
				 * get/put wrappers that intentionally only inc.
				 */
				if (max_net > 0 && any_has_dec)
					add_range(&leak_lines, line, line);
			}

			/* Excess put: some sub-path has net < 0 (more dec than inc).
			 * Warn on ANY path: net < 0 always indicates a real
			 * imbalance, even on success returns.
			 */
			if (min_net < 0 && any_has_inc)
				add_range(&excess_put_lines, line, line);
		}

	swap_stree:
		__swap_cur_stree(orig);
	} END_FOR_EACH_PTR(stree);

	/* Phase 3: report */
	if (leak_lines)
		sm_warning("refcount leak '%s' (fn: %s): lines='%s'",
			   name, get_refcount_fn_trace(name, sym),
			   show_rl(leak_lines));
	if (excess_put_lines)
		sm_warning("refcount excess put '%s' (fn: %s): lines='%s'",
			   name, get_refcount_fn_trace(name, sym),
			   show_rl(excess_put_lines));
}

static void process_states(void)
{
	struct sm_state *tmp;

	FOR_EACH_MY_SM(my_id, __get_cur_stree(), tmp) {
		check_count(tmp->name, tmp->sym);
	} END_FOR_EACH_SM(tmp);
}

static void process_states2(void)
{
	struct sm_state *tmp;

	FOR_EACH_MY_SM(my_id, __get_cur_stree(), tmp) {
		check_refcount_balance(tmp->name, tmp->sym);
	} END_FOR_EACH_SM(tmp);
}

/*
 * Cross-function DB hooks: when a callee's return_states has
 * type=REFCOUNT_INC(9027)/REFCOUNT_DEC(9028) records, these fire.
 * key example: "$->refs.refs.counter"
 */
static void db_return_inc(struct expression *expr, int param, char *key, char *value)
{
	match_inc(expr, key, NULL);
}

static void db_return_dec(struct expression *expr, int param, char *key, char *value)
{
	match_dec(expr, key, NULL);
}

static void record_return_info(int return_id, char *return_ranges,
			       struct expression *returned_expr,
			       int param, const char *printed_name,
			       struct sm_state *sm)
{
	struct smatch_state *state;
	int *counts, n;
	int min_net = INT_MAX, max_net = INT_MIN;

	if (param == -1 && return_ranges && strcmp(return_ranges, "0") == 0)
		return;

	state = sm->state;
	if (!state)
		return;

	parse_count_state(state, &counts, &n);
	for (int i = 0; i < n; i++) {
		if (counts[i] < min_net)
			min_net = counts[i];
		if (counts[i] > max_net)
			max_net = counts[i];
	}
	free(counts);

	/* A single return path may have sub-paths with both INC and DEC */
	if (max_net > 0)
		sql_insert_return_states(return_id, return_ranges, REFCOUNT_INC,
					 param, printed_name, "");
	if (min_net < 0)
		sql_insert_return_states(return_id, return_ranges, REFCOUNT_DEC,
					 param, printed_name, "");
	/* net==0 or no counts: nothing to export */
}

void check_refcount_inconsistent_returns(int id)
{
	my_id = id;

	if (option_project != PROJ_KERNEL)
		return;

	preserve_out_of_scope(id);

	/* custom merge: union function-trace lists instead of → merged */
	add_merge_hook(my_id, &refcount_trace_merge);

	/* same-file: func_table directly calls refcount_inc/dec hooks */
	add_refcount_init_hook(&match_inc);
	add_refcount_inc_hook(&match_inc);
	add_refcount_dec_hook(&match_dec);

	/* cross-file: DB return_states query */
	select_return_states_hook(REFCOUNT_INC, &db_return_inc);
	select_return_states_hook(REFCOUNT_DEC, &db_return_dec);

	/* export refcount states to DB */
	add_return_info_callback(my_id, &record_return_info);

	all_return_states_hook(&process_states);
	all_return_states_hook(&process_states2);
}
