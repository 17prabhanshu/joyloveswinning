
MEMORY {
    FLASH (rx) : ORIGIN = 0x00000000, LENGTH = 128K
    RAM (rwx) : ORIGIN = 0x20000000, LENGTH = 20K
}
SECTIONS {
    .text : {
        KEEP(*(.vectors))
        *(.text*)
        *(.rodata*)
    } > FLASH
    .data : { *(.data*) } > RAM AT > FLASH
    .bss : { *(.bss*) *(COMMON) } > RAM
}
