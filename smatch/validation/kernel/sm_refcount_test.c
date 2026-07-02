/*
 * Test for improved refcount checker — detects both leak and excess put.
 *
 * Uses refcount_inc/refcount_dec from the func_table.
 * Checker should report:
 *   - refcount leak on error paths where get has no matching put
 *   - refcount excess put where put occurs more times than get
 *   - balanced refcount where get/put are correctly paired
 */
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/refcount.h>

#include "../check_debug.h"

struct test_data {
	int x;
	refcount_t refs;
};

/* Case 1: Balanced — single inc/dec pair.
 * Expected: balanced (no warning)
 */
static int test_balanced(struct test_data *d, int err)
{
	refcount_inc(&d->refs);       /* +1 */
	/* use d->x */
	refcount_dec(&d->refs);       /* 0 */
	return 0;
}

/* Case 2: Simple excess put — one inc, two decs.
 * Expected: refcount excess put
 */
static int test_excess_put_simple(struct test_data *d, int err)
{
	refcount_inc(&d->refs);       /* +1 */
	refcount_dec(&d->refs);       /* 0 */
	refcount_dec(&d->refs);       /* -1 EXCESS! */
	return 0;
}

/* Case 3: Leak — inc without dec on error path.
 * Expected: refcount leak
 */
static int test_leak(struct test_data *d, int err)
{
	refcount_inc(&d->refs);       /* +1 */
	if (err)
		return -EINVAL;        /* LEAK: +1 at return */
	refcount_dec(&d->refs);       /* 0 */
	return 0;
}

/* Case 4: Post-merge excess put — cleanup label adds extra put.
 * Expected: refcount excess put (from error path through cleanup)
 */
static int test_excess_put_post_merge(struct test_data *d, int err)
{
	refcount_inc(&d->refs);       /* +1 */
	if (err) {
		refcount_dec(&d->refs); /* 0 (path A) */
		goto out;
	}
	/* path B: +1 */
out:
	refcount_dec(&d->refs);       /* path A: -1 EXCESS! path B: 0 */
	return 0;
}

/* Case 5: Two incs, one dec — leak.
 * Expected: refcount leak (net=+1 at return)
 */
static int test_double_inc_leak(struct test_data *d, int err)
{
	refcount_inc(&d->refs);       /* +1 */
	refcount_inc(&d->refs);       /* +2 */
	if (err)
		goto err_out;
	refcount_dec(&d->refs);       /* +1 */
	return 0;
err_out:
	return -EINVAL;               /* LEAK: +2 at return */
}

/*
 * check-name: smatch refcount excess put #1
 * check-command: validation/kernel/build.sh sm_refcount_test.c
 *
 * check-output-start
sm_refcount_test.c:41 test_excess_put_simple() warn: refcount excess put '$->refs.counter' (fn: inc:[refcount_inc] dec:[refcount_dec,refcount_dec])
sm_refcount_test.c:53 test_leak() warn: refcount leak '$->refs.counter' (fn: inc:[refcount_inc] dec:[refcount_dec]): lines='51'
sm_refcount_test.c:65 test_excess_put_post_merge() warn: refcount excess put '$->refs.counter' (fn: inc:[refcount_inc] dec:[refcount_dec,refcount_dec])
sm_refcount_test.c:82 test_double_inc_leak() warn: refcount leak '$->refs.counter' (fn: inc:[refcount_inc,refcount_inc] dec:[refcount_dec])
 * check-output-end
 */

MODULE_LICENSE("GPL");
