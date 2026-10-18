/* Shared firmware logic: built for the target and for host unit tests. */
#ifndef FWLIB_H
#define FWLIB_H

#include <stdint.h>
#include <stddef.h>

/* IEEE 802.3 CRC-32 (same polynomial as zlib.crc32). */
uint32_t fw_crc32(const void *data, size_t len);

/* Rollout cohort 0..99, stable per device: crc32(MAC) % 100. */
unsigned fw_cohort(const uint8_t mac[6]);

/* True if a device belongs to a rollout stage of `percent` (0..100).
 * Monotonic: a device in the 10 % stage is also in the 30 % stage. */
int fw_in_rollout(const uint8_t mac[6], unsigned percent);

/* Anti-rollback: accept an update only if its security version is
 * not lower than the one burned into the device. */
int fw_accept_update(uint32_t device_secver, uint32_t image_secver);

#endif
