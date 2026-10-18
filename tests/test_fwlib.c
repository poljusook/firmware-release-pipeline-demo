/* Host unit tests for fwlib. Minimal harness that writes JUnit XML so CI can
 * collect results and the flaky-test tooling can compare reruns. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include "fwlib.h"

typedef int (*test_fn)(void);
struct test { const char *name; test_fn fn; };

static int test_crc32_check_value(void)
{
    return fw_crc32("123456789", 9) == 0xCBF43926u;
}

static int test_cohort_in_range(void)
{
    uint8_t mac[6] = { 0 };
    for (unsigned i = 0; i < 10000; i++) {
        memcpy(mac + 2, &i, sizeof i);
        if (fw_cohort(mac) >= 100)
            return 0;
    }
    return 1;
}

/* 10 % stage should hold roughly 10 % of devices. */
static int test_cohort_distribution(void)
{
    uint8_t mac[6] = { 0x00, 0x1A };
    unsigned hits = 0, n = 20000;
    for (unsigned i = 0; i < n; i++) {
        memcpy(mac + 2, &i, sizeof i);
        hits += fw_in_rollout(mac, 10);
    }
    return hits > n * 8 / 100 && hits < n * 12 / 100;
}

static int test_rollout_monotonic(void)
{
    static const unsigned ladder[] = { 1, 10, 30, 100 };
    uint8_t mac[6] = { 0x00, 0x1A };
    for (unsigned i = 0; i < 5000; i++) {
        memcpy(mac + 2, &i, sizeof i);
        for (unsigned s = 0; s + 1 < 4; s++)
            if (fw_in_rollout(mac, ladder[s]) && !fw_in_rollout(mac, ladder[s + 1]))
                return 0;
    }
    return 1;
}

static int test_anti_rollback(void)
{
    return fw_accept_update(3, 3) && fw_accept_update(3, 4) && !fw_accept_update(3, 2);
}

/* Deliberately flaky when FLAKY_DEMO=1, to exercise quarantine tooling. */
static int test_flaky_demo(void)
{
    if (!getenv("FLAKY_DEMO"))
        return 1;
    srand((unsigned)time(NULL) ^ (unsigned)getpid());
    return rand() % 3 != 0;
}

static const struct test tests[] = {
    { "crc32_check_value",   test_crc32_check_value },
    { "cohort_in_range",     test_cohort_in_range },
    { "cohort_distribution", test_cohort_distribution },
    { "rollout_monotonic",   test_rollout_monotonic },
    { "anti_rollback",       test_anti_rollback },
    { "flaky_demo",          test_flaky_demo },
};

int main(int argc, char **argv)
{
    const char *xml_path = argc > 1 ? argv[1] : "unit.xml";
    size_t n = sizeof tests / sizeof tests[0];
    int failed = 0;
    int ok[sizeof tests / sizeof tests[0]];

    for (size_t i = 0; i < n; i++) {
        ok[i] = tests[i].fn();
        failed += !ok[i];
        printf("%-22s %s\n", tests[i].name, ok[i] ? "PASS" : "FAIL");
    }

    FILE *f = fopen(xml_path, "w");
    if (f) {
        fprintf(f, "<testsuite name=\"fwlib\" tests=\"%zu\" failures=\"%d\">\n", n, failed);
        for (size_t i = 0; i < n; i++) {
            fprintf(f, "  <testcase classname=\"fwlib\" name=\"%s\">", tests[i].name);
            if (!ok[i])
                fprintf(f, "<failure message=\"assertion failed\"/>");
            fprintf(f, "</testcase>\n");
        }
        fprintf(f, "</testsuite>\n");
        fclose(f);
    }
    return failed ? 1 : 0;
}
