/*
 * Copyright (C) 2026 Oracle.
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

/*
 * check_refcount_uaf.c: Detect use-after-release for refcount-managed objects.
 *
 * When a refcount_dec function decrements the refcount to zero, the
 * object's release callback runs and the object is freed.  Any subsequent
 * use of the object -- or of pointers derived from it (data containment) --
 * is a use-after-free bug.
 *
 * Hooks into add_refcount_dec_hook to monitor every refcount decrement.
 * Severity:
 *   sm_error   -- on atomic_dec_and_test path (confirmed last put)
 *   sm_warning -- otherwise (conservative: might be last put)
 */

#include "smatch.h"
#include "smatch_extra.h"
#include "smatch_slist.h"

static int my_id;

STATE(refcount_released);
STATE(refcount_maybe_released);
STATE(ok);

/* ---------- helpers ---------- */

static void ok_to_use(struct sm_state *sm, struct expression *mod_expr)
{
	if (sm->state != &ok)
		set_state(my_id, sm->name, sm->sym, &ok);
}

static int uaf_severity(void)
{
	if (on_atomic_dec_path())
		return 1;
	return 0;
}

/*
 * Check if 'expr' refers to a member of a released parent object
 * (data containment).  Walk backwards through & or -> to find the
 * parent, then check if parent is released.
 */
static bool parent_is_refcount_released(struct expression *expr)
{
	struct expression *tmp;
	struct smatch_state *state;
	const char *name;
	struct symbol *sym;
	char n[256];

	tmp = expr;
	while (tmp) {
		if (tmp->type == EXPR_PREOP && tmp->op == '&')
			tmp = strip_expr(tmp->unop);
		else if (tmp->type == EXPR_DEREF &&
			 tmp->deref->type == EXPR_PREOP &&
			 tmp->deref->op == '*')
			tmp = strip_expr(tmp->member);
		else
			break;
	}

	name = expr_to_var_sym(tmp, &sym);
	if (!name || !sym)
		return false;

	state = get_state(my_id, name, NULL);
	if (state == &refcount_released || state == &refcount_maybe_released)
		return true;

	/*
	 * Strip ->field suffixes one level at a time to check if any
	 * parent object in the containment chain is released.
	 * e.g. for "container->sub->data", first try "container->sub",
	 * then "container".
	 */
	snprintf(n, sizeof(n), "%s", name);
	while (true) {
		char *arrow = strrchr(n, '>');
		if (!arrow || arrow <= n || *(arrow - 1) != '-')
			break;
		*(arrow - 1) = '\0';
		state = get_state(my_id, n, NULL);
		if (state == &refcount_released || state == &refcount_maybe_released)
			return true;
	}

	return false;
}

static int get_released_line(struct expression *expr, const char *name,
			      struct symbol *sym)
{
	struct sm_state *sm, *tmp;
	int line = -1;

	/* Use NULL sym so the lookup matches regardless of which
	 * sub-expression the symbol was originally derived from.
	 */
	sm = get_sm_state(my_id, name, NULL);
	if (!sm)
		return -1;

	FOR_EACH_PTR(sm->possible, tmp) {
		if (tmp->state == &refcount_released ||
		    tmp->state == &refcount_maybe_released) {
			line = tmp->line;
			break;
		}
	} END_FOR_EACH_PTR(tmp);

	return line;
}

/* ---------- hook callbacks ---------- */

/*
 * Known counter path suffix patterns that can be stripped from a
 * param_key name to find the parent object.  Ordered longest-first
 * so that "->kref.refcount.refs.counter" matches before ".counter".
 */
static const char * const counter_suffixes[] = {
	/* refcount_t-style (->refs.counter) — full paths */
	"->kref.refcount.refs.counter",
	"->refcount.refcount.refs.counter",
	"->ref.refcount.refs.counter",
	"->refcnt.refcount.refs.counter",
	"->refcount.refs.counter",
	"->refcnt.refs.counter",
	"->users.refs.counter",
	"->usage.refs.counter",
	"->use.refs.counter",
	"->active_users.refs.counter",
	"->count.count.refs.counter",
	"->count.refs.counter",
	"->nref.refs.counter",
	"->dev_refcnt.refs.counter",
	"->dlm_refs.refcount.refs.counter",
	"->f_count.counter",
	"->ref_count.refs.counter",
	"->module.refcnt.counter",
	"->btf.refcnt.refs.counter",
	".refs.counter",
	/* atomic_t-style (.counter) inside wrapper structs —
	 * when atomic_dec_and_test(&obj->kref.refcount) produces
	 * name="obj->kref.refcount.counter", strip the FULL path */
	"->kref.refcount.counter",
	"->refcount.counter",
	"->refcnt.counter",
	"->ref.counter",
	"->count.counter",
	".kref.refcount.counter",
	".refcount.counter",
	".refcnt.counter",
	".ref.counter",
	".count.counter",
	/* generic atomic_t counter — checked LAST */
	"->counter",
	".counter",
};

static const char *strip_counter_suffix(const char *name)
{
	char buf[256];
	int i;

	snprintf(buf, sizeof(buf), "%s", name);
	for (i = 0; i < ARRAY_SIZE(counter_suffixes); i++) {
		const char *suffix = counter_suffixes[i];
		char *p = strstr(buf, suffix);

		if (p) {
			*p = '\0';
			return alloc_string(buf);
		}
	}
	/* unknown pattern — return full name as fallback */
	return alloc_string(name);
}

/*
 * Called when any refcount decrement happens.
 * Mark the parent object as potentially released.
 */
static void match_refcount_dec(struct expression *expr, const char *name,
				struct symbol *sym)
{
	struct smatch_state *state_to_set;
	const char *parent_name;

	if (on_atomic_dec_path())
		state_to_set = &refcount_released;
	else
		state_to_set = &refcount_maybe_released;

	/*
	 * Strip known counter path suffixes from 'name' (the full param_key
	 * path like "obj->refcount.refs.counter") to find the parent object
	 * name (e.g. "obj").  Use NULL sym so that lookups match regardless
	 * of which sub-expression the symbol comes from.
	 */
	parent_name = strip_counter_suffix(name);
	set_state(my_id, parent_name, NULL, state_to_set);
}

/* SYM_HOOK: any symbol reference */
static void match_symbol(struct expression *expr)
{
	struct expression *parent;
	char *name;
	struct symbol *sym;
	int line, sev;

	if (is_impossible_path())
		return;
	if (__in_fake_parameter_assign)
		return;
	if (is_part_of_condition(expr))
		return;

	/* ignore "get_new_ptr(&foo);" */
	parent = expr_get_parent_expr(expr);
	while (parent && parent->type == EXPR_PREOP && parent->op == '(')
		parent = expr_get_parent_expr(parent);
	if (parent && parent->type == EXPR_PREOP && parent->op == '&')
		return;

	name = expr_to_var_sym(expr, &sym);
	if (!name || !sym)
		return;

	line = get_released_line(expr, name, sym);
	if (line < 0 && parent_is_refcount_released(expr))
		line = 0;
	if (line < 0)
		return;

	sev = uaf_severity();
	if (sev)
		sm_error("using '%s' after refcount release (line %d)", name, line);
	else
		sm_warning("using '%s' after possible refcount release (line %d)",
			   name, line);
}

/* deref_hook: actual dereference */
static void deref_hook(struct expression *expr)
{
	char *name;
	struct symbol *sym;
	int line, sev;

	if (__in_fake_parameter_assign)
		return;
	if (is_impossible_path())
		return;

	name = expr_to_var_sym(expr, &sym);
	if (!name || !sym)
		return;

	line = get_released_line(expr, name, sym);
	if (line < 0)
		return;

	sev = uaf_severity();
	if (sev)
		sm_error("dereferencing '%s' after refcount release (line %d)", name, line);
	else
		sm_warning("dereferencing '%s' after possible refcount release (line %d)",
			   name, line);
	set_state_expr(my_id, expr, &ok);
}

/* RETURN_HOOK: returning released pointer */
static void match_return(struct expression *expr)
{
	char *name;
	struct symbol *sym;
	int line, sev;

	if (is_impossible_path())
		return;
	if (type_bits(cur_func_return_type()) <= 1)
		return;

	name = expr_to_var_sym(expr, &sym);
	if (!name || !sym)
		return;

	line = get_released_line(expr, name, sym);
	if (line < 0)
		return;

	sev = uaf_severity();
	if (sev)
		sm_error("returning '%s' after refcount release (line %d)", name, line);
	else
		sm_warning("returning '%s' after possible refcount release (line %d)",
			   name, line);
}

/* FUNCTION_CALL_HOOK: passing released pointer to a function */
static void match_call(struct expression *expr)
{
	struct expression *arg;
	char *name;
	struct symbol *sym;
	int line, i, sev;

	if (is_impossible_path())
		return;

	i = -1;
	FOR_EACH_PTR(expr->args, arg) {
		i++;
		if (!is_pointer(arg))
			continue;

		name = expr_to_var_sym(arg, &sym);
		if (!name || !sym)
			continue;

		line = get_released_line(arg, name, sym);
		if (line < 0)
			continue;

		sev = uaf_severity();
		if (sev)
			sm_error("passing '%s' after refcount release (line %d)",
				 name, line);
		else
			sm_warning("passing '%s' after possible refcount release (line %d)",
				   name, line);
		set_state_expr(my_id, arg, &ok);
	} END_FOR_EACH_PTR(arg);
}

/* ---------- registration ---------- */

void check_refcount_uaf(int id)
{
	my_id = id;

	if (option_project != PROJ_KERNEL)
		return;

	add_refcount_dec_hook(&match_refcount_dec);
	add_dereference_hook(deref_hook);
	add_hook(&match_symbol, SYM_HOOK);
	add_hook(&match_return, RETURN_HOOK);
	add_hook(&match_call, FUNCTION_CALL_HOOK);
	add_modification_hook_late(my_id, &ok_to_use);
}
