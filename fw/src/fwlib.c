#include "fwlib.h"

uint32_t fw_crc32(const void *data, size_t len)
{
    const uint8_t *p = data;
    uint32_t crc = 0xFFFFFFFFu;

    while (len--) {
        crc ^= *p++;
        for (int i = 0; i < 8; i++)
            crc = (crc >> 1) ^ (0xEDB88320u & (0u - (crc & 1u)));
    }
    return ~crc;
}

unsigned fw_cohort(const uint8_t mac[6])
{
    return fw_crc32(mac, 6) % 100u;
}

int fw_in_rollout(const uint8_t mac[6], unsigned percent)
{
    return fw_cohort(mac) < percent;
}

int fw_accept_update(uint32_t device_secver, uint32_t image_secver)
{
    return image_secver >= device_secver;
}
