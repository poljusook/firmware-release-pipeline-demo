# Release pipeline demo. Every CI stage is a make target, so Jenkins, GitHub
# Actions and a laptop all run the same commands.

CROSS    ?= arm-none-eabi-
CC_ARM   := $(CROSS)gcc
OBJCOPY  := $(CROSS)objcopy
SIZE     := $(CROSS)size
HOSTCC   ?= gcc
QEMU     ?= qemu-system-arm
B        := build

VERSION  := $(shell git describe --tags --match 'v*' --always --dirty 2>/dev/null || echo 0.0.0-dev)
BUILD_ID := $(shell git rev-parse --short=12 HEAD 2>/dev/null || echo unknown)
SECVER   := $(shell cat SECVER)

ARM_FLAGS := -mcpu=cortex-m3 -mthumb -Os -g -Wall -Wextra -Werror \
             -ffunction-sections -fdata-sections -ffreestanding -nostdlib \
             -Ifw/include -I$(B)
LD_FLAGS  := -Tfw/cm3.ld -Wl,--gc-sections -Wl,-Map=$(B)/fw.map

FW_SRC := fw/src/startup.c fw/src/main.c fw/src/fwlib.c
IMAGE  := $(B)/fw-$(VERSION).bin

.PHONY: all fw test-unit test-qemu manifest changelog gate clean
all: fw test-unit test-qemu manifest

# version.h is rewritten only when its content changes, so builds stay incremental.
$(B)/version.h: FORCE
	@mkdir -p $(B)
	@printf '#define FW_VERSION "%s"\n#define FW_BUILD_ID "%s"\n#define FW_SECVER %su\n' \
	    "$(VERSION)" "$(BUILD_ID)" "$(SECVER)" > $@.tmp
	@cmp -s $@.tmp $@ && rm $@.tmp || mv $@.tmp $@
FORCE:

$(B)/fw.elf: $(FW_SRC) fw/cm3.ld $(B)/version.h
	$(CC_ARM) $(ARM_FLAGS) $(FW_SRC) $(LD_FLAGS) -o $@
	$(SIZE) $@

$(IMAGE): $(B)/fw.elf
	$(OBJCOPY) -O binary $< $@

fw: $(IMAGE)

$(B)/test_fwlib: tests/test_fwlib.c fw/src/fwlib.c fw/include/fwlib.h
	@mkdir -p $(B)
	$(HOSTCC) -O1 -Wall -Wextra -Werror -Ifw/include tests/test_fwlib.c fw/src/fwlib.c -o $@

test-unit: $(B)/test_fwlib
	$(B)/test_fwlib $(B)/unit.xml

# Smoke test on an emulated Cortex-M3: stands in for a HIL run on an EVB.
test-qemu: $(B)/fw.elf
	python3 tools/qemu_smoke.py --qemu $(QEMU) --elf $< --expect-version $(VERSION) --junit $(B)/qemu.xml

manifest: $(IMAGE)
	python3 tools/manifest.py --image $(IMAGE) --version $(VERSION) --out $(B)/manifest.json

changelog:
	python3 tools/changelog.py --out $(B)/CHANGELOG.md

gate: manifest
	python3 tools/gate.py --manifest $(B)/manifest.json --junit $(B)/unit.xml $(B)/qemu.xml \
	    --blocklist blocklist.txt --quarantine quarantine.json --budget 131072

clean:
	rm -rf $(B)
