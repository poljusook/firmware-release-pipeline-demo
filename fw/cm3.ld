/* LM3S6965 memory map (QEMU lm3s6965evb). APP_BUDGET models the size of an
 * application slot: half of flash, so two images (A/B) fit side by side. */
MEMORY
{
    FLASH (rx)  : ORIGIN = 0x00000000, LENGTH = 256K
    RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 64K
}

APP_BUDGET = 128K;
_estack = ORIGIN(RAM) + LENGTH(RAM);

SECTIONS
{
    .text :
    {
        KEEP(*(.isr_vector))
        . = 0x40;
        KEEP(*(.fw_info))
        *(.text*)
        *(.rodata*)
        . = ALIGN(4);
    } > FLASH

    _sidata = LOADADDR(.data);
    .data :
    {
        _sdata = .;
        *(.data*)
        . = ALIGN(4);
        _edata = .;
    } > RAM AT > FLASH

    .bss (NOLOAD) :
    {
        _sbss = .;
        *(.bss*) *(COMMON)
        . = ALIGN(4);
        _ebss = .;
    } > RAM

    _image_end = LOADADDR(.data) + SIZEOF(.data);
}

/* Fail the build at link time, not in the field. */
ASSERT(_image_end - ORIGIN(FLASH) <= APP_BUDGET, "image exceeds APP_BUDGET (one A/B slot)")
