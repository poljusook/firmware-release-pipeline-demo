/* Demo firmware for a Cortex-M3 (QEMU lm3s6965evb, same core as Talaria TWO).
 * Prints its identity, runs a power-on self-test, exits through semihosting. */
#include "fwlib.h"
#include "version.h"

#define UART0_DR (*(volatile uint32_t *)0x4000C000u)

/* Identity record at a fixed spot right after the vector table, so release
 * tooling can read the stamped version straight out of the binary. */
struct fw_info {
    char     magic[8];
    char     version[32];
    char     build_id[16];
    uint32_t secver;
};

__attribute__((section(".fw_info"), used))
const struct fw_info fw_info = {
    .magic    = "FWINFO1",
    .version  = FW_VERSION,
    .build_id = FW_BUILD_ID,
    .secver   = FW_SECVER,
};

static void puts_uart(const char *s)
{
    while (*s)
        UART0_DR = (uint32_t)*s++;
}

static void put_hex(uint32_t v)
{
    static const char hex[] = "0123456789abcdef";
    for (int i = 28; i >= 0; i -= 4)
        UART0_DR = (uint32_t)hex[(v >> i) & 0xF];
}

static int selftest(void)
{
    static const uint8_t mac[6] = { 0x00, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E };

    if (fw_crc32("123456789", 9) != 0xCBF43926u)
        return 0;
    if (fw_in_rollout(mac, 10) && !fw_in_rollout(mac, 30))
        return 0;
    if (!fw_accept_update(FW_SECVER, FW_SECVER))
        return 0;
    return 1;
}

/* ARM semihosting SYS_EXIT: QEMU exits 0 on ApplicationExit, 1 otherwise. */
static void semihost_exit(int ok)
{
    register uint32_t r0 __asm__("r0") = 0x18;
    register uint32_t r1 __asm__("r1") = ok ? 0x20026u : 0x20023u;
    __asm__ volatile("bkpt 0xAB" : : "r"(r0), "r"(r1) : "memory");
}

int main(void)
{
    puts_uart("BOOT version=" FW_VERSION " build=" FW_BUILD_ID " secver=0x");
    put_hex(FW_SECVER);
    puts_uart("\n");

    int ok = selftest();
    puts_uart(ok ? "SELFTEST PASS\n" : "SELFTEST FAIL\n");
    semihost_exit(ok);
    for (;;)
        ;
}
