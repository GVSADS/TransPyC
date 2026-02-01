import c
import t

# ================================= 原始顺序开始 =================================
# struct BOOTINFO
class BOOTINFO(t.CStruct):
    cyls: t.CChar
    leds: t.CChar
    vmode: t.CChar
    reserve: t.CChar
    scrnx: t.CShort
    scrny: t.CShort
    vram: t.CChar | t.CPtr

# 宏定义
ADR_BOOTINFO: t.CDefine = 0x00000ff0
ADR_DISKIMG: t.CDefine = 0x00100000

# 函数声明 - void
def io_hlt() -> c.State: pass
def io_cli() -> c.State: pass
def io_sti() -> c.State: pass
def io_stihlt() -> c.State: pass
# 函数声明 - int
def io_in8(port: t.CInt) -> t.CInt | c.State: pass
# 函数声明 - void
def io_out8(port: t.CInt, data: t.CInt) -> c.State: pass
# 函数声明 - int
def io_load_eflags() -> t.CInt | c.State: pass
# 函数声明 - void
def io_store_eflags(eflags: t.CInt) -> c.State: pass
def load_gdtr(limit: t.CInt, addr: t.CInt) -> c.State: pass
def load_idtr(limit: t.CInt, addr: t.CInt) -> c.State: pass
# 函数声明 - int
def load_cr0() -> t.CInt | c.State: pass
# 函数声明 - void
def store_cr0(cr0: t.CInt) -> c.State: pass
def load_tr(tr: t.CInt) -> c.State: pass
def asm_inthandler0c() -> c.State: pass
def asm_inthandler0d() -> c.State: pass
def asm_inthandler20() -> c.State: pass
def asm_inthandler21() -> c.State: pass
def asm_inthandler2c() -> c.State: pass
# 函数声明 - unsigned int
def memtest_sub(start: t.CUnsignedInt, end: t.CUnsignedInt) -> t.CUnsignedInt | c.State: pass
# 函数声明 - void
def farjmp(eip: t.CInt, cs: t.CInt) -> c.State: pass
def farcall(eip: t.CInt, cs: t.CInt) -> c.State: pass
def asm_exw_api() -> c.State: pass
def start_app(eip: t.CInt, cs: t.CInt, esp: t.CInt, ds: t.CInt, tss_esp0: t.CInt | t.CPtr) -> c.State: pass
def asm_end_app() -> c.State: pass

# struct FIFO32
class FIFO32(t.CStruct):
    buf: t.CInt | t.CPtr
    p: t.CInt
    q: t.CInt
    size: t.CInt
    free: t.CInt
    flags: t.CInt
    task: t.CStruct(name="TASK") | t.CPtr

# 函数声明 - void
def fifo32_init(fifo: t.CStruct(name="FIFO32") | t.CPtr, size: t.CInt, buf: t.CInt | t.CPtr, task: t.CStruct(name="TASK") | t.CPtr) -> c.State: pass
# 函数声明 - int
def fifo32_put(fifo: t.CStruct(name="FIFO32") | t.CPtr, data: t.CInt) -> t.CInt | c.State: pass
def fifo32_get(fifo: t.CStruct(name="FIFO32") | t.CPtr) -> t.CInt | c.State: pass
def fifo32_status(fifo: t.CStruct(name="FIFO32") | t.CPtr) -> t.CInt | c.State: pass

# 函数声明 - void
def init_color() -> c.State: pass
def set_color(start: t.CInt, end: t.CInt, rgb: t.CUnsignedChar | t.CPtr) -> c.State: pass
def boxfill8(vram: t.CUnsignedChar | t.CPtr, xsize: t.CInt, c: t.CUnsignedChar, x0: t.CInt, y0: t.CInt, x1: t.CInt, y1: t.CInt) -> c.State: pass
def init_desktop(vram: t.CChar | t.CPtr, x: t.CInt, y: t.CInt) -> c.State: pass
def putfont8(vram: t.CChar | t.CPtr, xsize: t.CInt, x: t.CInt, y: t.CInt, c: t.CChar, font: t.CChar | t.CPtr) -> c.State: pass
def putfonts8_asc(vram: t.CChar | t.CPtr, xsize: t.CInt, x: t.CInt, y: t.CInt, c: t.CChar, s: t.CUnsignedChar | t.CPtr) -> c.State: pass
def init_mouse_cursor8(mouse: t.CChar | t.CPtr, bc: t.CChar) -> c.State: pass
def init_mouse_pen_cursor8(mouse: t.CChar | t.CPtr, bc: t.CChar) -> c.State: pass
def putblock8_8(vram: t.CChar | t.CPtr, vxsize: t.CInt, pxsize: t.CInt, pysize: t.CInt, px0: t.CInt, py0: t.CInt, buf: t.CChar | t.CPtr, bxsize: t.CInt) -> c.State: pass
# 函数声明 - int
def read_picture(fat: t.CInt | t.CPtr, vram: t.CChar | t.CPtr, x: t.CInt, y: t.CInt) -> t.CInt | c.State: pass

# 颜色宏定义
COL8_000000: t.CDefine = 0
COL8_FF0000: t.CDefine = 1
COL8_00FF00: t.CDefine = 2
COL8_FFFF00: t.CDefine = 3
COL8_0000FF: t.CDefine = 4
COL8_FF00FF: t.CDefine = 5
COL8_00FFFF: t.CDefine = 6
COL8_FFFFFF: t.CDefine = 7
COL8_C6C6C6: t.CDefine = 8
COL8_840000: t.CDefine = 9
COL8_008400: t.CDefine = 10
COL8_848400: t.CDefine = 11
COL8_000084: t.CDefine = 12
COL8_840084: t.CDefine = 13
COL8_008484: t.CDefine = 14
COL8_848484: t.CDefine = 15
COL8_202020: t.CDefine = 16
COL8_RWL: t.CDefine = 16
COL8_252525: t.CDefine = 17

# struct DLL_STRPICENV
class DLL_STRPICENV(t.CStruct):
    work: t.CInt[64 * 1024 // 4]

# struct RGB
class RGB(t.CStruct):
    b: t.CUnsignedChar
    g: t.CUnsignedChar
    r: t.CUnsignedChar
    t: t.CUnsignedChar

# 函数声明 - int
def info_JPEG(env: t.CStruct(name="DLL_STRPICENV") | t.CPtr, info: t.CInt | t.CPtr, size: t.CInt, fp: t.CUnsignedChar | t.CPtr) -> t.CInt | c.State: pass
def decode0_JPEG(env: t.CStruct(name="DLL_STRPICENV") | t.CPtr, size: t.CInt, fp: t.CUnsignedChar | t.CPtr, b_type: t.CInt, buf: t.CUnsignedChar | t.CPtr, skip: t.CInt) -> t.CInt | c.State: pass

# struct SEGMENT_DESCRIPTOR
class SEGMENT_DESCRIPTOR(t.CStruct):
    limit_low: t.CShort
    base_low: t.CShort
    base_mid: t.CChar
    access_right: t.CChar
    limit_high: t.CChar
    base_high: t.CChar

# struct GATE_DESCRIPTOR
class GATE_DESCRIPTOR(t.CStruct):
    offset_low: t.CShort
    selector: t.CShort
    dw_count: t.CChar
    access_right: t.CChar
    offset_high: t.CShort

# 函数声明 - void
def init_gdtidt() -> c.State: pass
def set_segmdesc(sd: t.CStruct(name="SEGMENT_DESCRIPTOR") | t.CPtr, limit: t.CUnsignedInt, base: t.CInt, ar: t.CInt) -> c.State: pass
def set_gatedesc(gd: t.CStruct(name="GATE_DESCRIPTOR") | t.CPtr, offset: t.CInt, selector: t.CInt, ar: t.CInt) -> c.State: pass

# 宏定义
ADR_IDT: t.CDefine = 0x0026f800
LIMIT_IDT: t.CDefine = 0x000007ff
ADR_GDT: t.CDefine = 0x00270000
LIMIT_GDT: t.CDefine = 0x0000ffff
ADR_BOTPAK: t.CDefine = 0x00280000
LIMIT_BOTPAK: t.CDefine = 0x0007ffff
AR_DATA32_RW: t.CDefine = 0x4092
AR_CODE32_ER: t.CDefine = 0x409a
AR_LDT: t.CDefine = 0x0082
AR_TSS32: t.CDefine = 0x0089
AR_INTGATE32: t.CDefine = 0x008e

# 函数声明 - void
def init_pic() -> c.State: pass

# 宏定义
PIC0_ICW1: t.CDefine = 0x0020
PIC0_OCW2: t.CDefine = 0x0020
PIC0_IMR: t.CDefine = 0x0021
PIC0_ICW2: t.CDefine = 0x0021
PIC0_ICW3: t.CDefine = 0x0021
PIC0_ICW4: t.CDefine = 0x0021
PIC1_ICW1: t.CDefine = 0x00a0
PIC1_OCW2: t.CDefine = 0x00a0
PIC1_IMR: t.CDefine = 0x00a1
PIC1_ICW2: t.CDefine = 0x00a1
PIC1_ICW3: t.CDefine = 0x00a1
PIC1_ICW4: t.CDefine = 0x00a1

# 函数声明 - void
def inthandler21(esp: t.CInt | t.CPtr) -> c.State: pass
def wait_KBC_sendready() -> c.State: pass
def init_keyboard(fifo: t.CStruct(name="FIFO32") | t.CPtr, data0: t.CInt) -> c.State: pass

# 宏定义
PORT_KEYDAT: t.CDefine = 0x0060
PORT_KEYCMD: t.CDefine = 0x0064

# struct MOUSE_DEC
class MOUSE_DEC(t.CStruct):
    buf: t.CUnsignedChar[3]
    phase: t.CChar
    x: t.CInt
    y: t.CInt
    btn: t.CInt

# 函数声明 - void
def inthandler2c(esp: t.CInt | t.CPtr) -> c.State: pass
# 函数声明 - void
def enable_mouse(fifo: t.CStruct(name="FIFO32") | t.CPtr, data0: t.CInt, mdec: t.CStruct(name="MOUSE_DEC") | t.CPtr) -> c.State: pass
# 函数声明 - int
def mouse_decode(mdec: t.CStruct(name="MOUSE_DEC") | t.CPtr, dat: t.CUnsignedChar) -> t.CInt | c.State: pass

# 宏定义
MEMMAN_FREES: t.CDefine = 4090
MEMMAN_ADDR: t.CDefine = 0x003c0000

# struct FREEINFO
class FREEINFO(t.CStruct):
    addr: t.CUnsignedInt
    size: t.CUnsignedInt

# struct MEMMAN
class MEMMAN(t.CStruct):
    frees: t.CInt
    maxfrees: t.CInt
    lostsize: t.CInt
    losts: t.CInt
    free: t.CStruct(name="FREEINFO")[MEMMAN_FREES]

def memtest(start: t.CUnsignedInt, end: t.CUnsignedInt) -> t.CUnsignedInt | c.State: pass
def memman_init(man: t.CStruct(name="MEMMAN") | t.CPtr) -> c.State: pass
def memman_total(man: t.CStruct(name="MEMMAN") | t.CPtr) -> t.CUnsignedInt | c.State: pass
def memman_alloc(man: t.CStruct(name="MEMMAN") | t.CPtr, size: t.CUnsignedInt) -> t.CUnsignedInt | c.State: pass
def memman_free(man: t.CStruct(name="MEMMAN") | t.CPtr, addr: t.CUnsignedInt, size: t.CUnsignedInt) -> t.CInt | c.State: pass
def memman_alloc_4k(man: t.CStruct(name="MEMMAN") | t.CPtr, size: t.CUnsignedInt) -> t.CUnsignedInt | c.State: pass
def memman_free_4k(man: t.CStruct(name="MEMMAN") | t.CPtr, addr: t.CUnsignedInt, size: t.CUnsignedInt) -> t.CInt | c.State: pass

# 宏定义
MAX_SHEETS: t.CDefine = 256

# struct SHEET
class SHEET(t.CStruct):
    buf: t.CUnsignedChar | t.CPtr
    bxsize: t.CInt
    bysize: t.CInt
    vx0: t.CInt
    vy0: t.CInt
    col_inv: t.CInt
    height: t.CInt
    flags: t.CInt
    ctl: t.CStruct(name="SHTCTL") | t.CPtr
    task: t.CStruct(name="TASK") | t.CPtr
    task2: t.CStruct(name="TASK")

# struct SHTCTL
class SHTCTL(t.CStruct):
    vram: t.CUnsignedChar | t.CPtr
    map: t.CUnsignedChar | t.CPtr
    xsize: t.CInt
    ysize: t.CInt
    top: t.CInt
    sheets: t.CPtr | t.CStruct(name="SHEET")[MAX_SHEETS]
    sheets0: t.CStruct(name="SHEET")[MAX_SHEETS]

# 函数声明 - struct SHTCTL*
def shtctl_init(memman: t.CStruct(name="MEMMAN") | t.CPtr, vram: t.CUnsignedChar | t.CPtr, xsize: t.CInt, ysize: t.CInt) -> t.CStruct(name="SHTCTL") | t.CPtr | c.State: pass
# 函数声明 - struct SHEET*
def sheet_alloc(ctl: t.CStruct(name="SHTCTL") | t.CPtr) -> t.CStruct(name="SHEET") | t.CPtr | c.State: pass
# 函数声明 - void
def sheet_setbuf(sht: t.CStruct(name="SHEET") | t.CPtr, buf: t.CUnsignedChar | t.CPtr, xsize: t.CInt, ysize: t.CInt, col_inv: t.CInt) -> c.State: pass
def sheet_updown(sht: t.CStruct(name="SHEET") | t.CPtr, height: t.CInt) -> c.State: pass
def sheet_refresh(sht: t.CStruct(name="SHEET") | t.CPtr, bx0: t.CInt, by0: t.CInt, bx1: t.CInt, by1: t.CInt) -> c.State: pass
def sheet_slide(sht: t.CStruct(name="SHEET") | t.CPtr, vx0: t.CInt, vy0: t.CInt) -> c.State: pass
def sheet_free(sht: t.CStruct(name="SHEET") | t.CPtr) -> c.State: pass

# 宏定义
MAX_TIMER: t.CDefine = 500

# struct TIMER
class TIMER(t.CStruct):
    next: t.CStruct(name="TIMER") | t.CPtr
    timeout: t.CUnsignedInt
    flags: t.CChar
    flags2: t.CChar
    fifo: t.CStruct(name="FIFO32") | t.CPtr
    data: t.CInt

# struct TIMERCTL
class TIMERCTL(t.CStruct):
    count: t.CUnsignedInt
    next: t.CUnsignedInt
    t0: t.CStruct(name="TIMER") | t.CPtr
    timers0: t.CStruct(name="TIMER")[MAX_TIMER]

# 外部全局变量
timerctl: t.CExtern | t.CStruct(name="TIMERCTL") = c.State

# 函数声明 - void
def init_pit() -> c.State: pass
# 函数声明 - struct TIMER*
def timer_alloc() -> t.CStruct(name="TIMER") | t.CPtr | c.State: pass
# 函数声明 - void
def timer_free(timer: t.CStruct(name="TIMER") | t.CPtr) -> c.State: pass
def timer_init(timer: t.CStruct(name="TIMER") | t.CPtr, fifo: t.CStruct(name="FIFO32") | t.CPtr, data: t.CInt) -> c.State: pass
def timer_settime(timer: t.CStruct(name="TIMER") | t.CPtr, timeout: t.CUnsignedInt) -> c.State: pass
# 函数声明 - void
def inthandler20(esp: t.CInt | t.CPtr) -> c.State: pass
# 函数声明 - int
def timer_cancel(timer: t.CStruct(name="TIMER") | t.CPtr) -> t.CInt | c.State: pass
# 函数声明 - void
def timer_cancelall(fifo: t.CStruct(name="FIFO32") | t.CPtr) -> c.State: pass

# 宏定义
MAX_TASKS: t.CDefine = 1000
TASK_GDT0: t.CDefine = 3
MAX_TASKS_LV: t.CDefine = 100
MAX_TASKLEVELS: t.CDefine = 10

# struct TSS32
class TSS32(t.CStruct):
    backlink: t.CInt
    esp0: t.CInt
    ss0: t.CInt
    esp1: t.CInt
    ss1: t.CInt
    esp2: t.CInt
    ss2: t.CInt
    cr3: t.CInt
    eip: t.CInt
    eflags: t.CInt
    eax: t.CInt
    ecx: t.CInt
    edx: t.CInt
    ebx: t.CInt
    esp: t.CInt
    ebp: t.CInt
    esi: t.CInt
    edi: t.CInt
    es: t.CInt
    cs: t.CInt
    ss: t.CInt
    ds: t.CInt
    fs: t.CInt
    gs: t.CInt
    ldtr: t.CInt
    iomap: t.CInt

# struct TASK
class TASK(t.CStruct):
    sel: t.CInt
    flags: t.CInt
    level: t.CInt
    priority: t.CInt
    fifo: t.CStruct(name="FIFO32")
    tss: t.CStruct(name="TSS32")
    ldt: t.CStruct(name="SEGMENT_DESCRIPTOR")[2]
    cons: t.CStruct(name="CONSOLE") | t.CPtr
    ds_base: t.CInt
    cons_stack: t.CInt
    fhandle: t.CStruct(name="FILEHANDLE") | t.CPtr
    fat: t.CInt | t.CPtr
    cmdline: t.CChar | t.CPtr
    langmode: t.CUnsignedChar
    langbyte1: t.CUnsignedChar

# struct TASKLEVEL
class TASKLEVEL(t.CStruct):
    running: t.CInt
    now: t.CInt
    tasks: t.CStruct(name="TASK") | t.CPtr[MAX_TASKS_LV]

# struct TASKCTL
class TASKCTL(t.CStruct):
    now_lv: t.CInt
    lv_change: t.CChar
    level: t.CStruct(name="TASKLEVEL")[MAX_TASKLEVELS]
    tasks0: t.CStruct(name="TASK")[MAX_TASKS]

# 外部全局变量
taskctl: t.CExtern | t.CStruct(name="TASKCTL") | t.CPtr = c.State
task_timer: t.CExtern | t.CStruct(name="TIMER") | t.CPtr = c.State

# 函数声明 - struct TASK*
def task_now() -> t.CStruct(name="TASK") | t.CPtr | c.State: pass
def task_init(memman: t.CStruct(name="MEMMAN") | t.CPtr) -> t.CStruct(name="TASK") | t.CPtr | c.State: pass
def task_alloc() -> t.CStruct(name="TASK") | t.CPtr | c.State: pass
# 函数声明 - void
def task_run(task: t.CStruct(name="TASK") | t.CPtr, level: t.CInt, priority: t.CInt) -> c.State: pass
def task_switch() -> c.State: pass
def task_sleep(task: t.CStruct(name="TASK") | t.CPtr) -> c.State: pass

# 函数声明 - void
def make_window8(buf: t.CUnsignedChar | t.CPtr, xsize: t.CInt, ysize: t.CInt, title: t.CChar | t.CPtr, act: t.CChar) -> c.State: pass
def putfonts8_asc_sht(sht: t.CStruct(name="SHEET") | t.CPtr, x: t.CInt, y: t.CInt, c: t.CInt, b: t.CInt, s: t.CChar | t.CPtr, l: t.CInt) -> c.State: pass
def make_textbox8(sht: t.CStruct(name="SHEET") | t.CPtr, x0: t.CInt, y0: t.CInt, sx: t.CInt, sy: t.CInt, c: t.CInt) -> c.State: pass
def make_wtitle8(buf: t.CUnsignedChar | t.CPtr, xsize: t.CInt, title: t.CChar | t.CPtr, act: t.CChar) -> c.State: pass
def change_wtitle8(sht: t.CStruct(name="SHEET") | t.CPtr, act: t.CChar) -> c.State: pass

# struct CONSOLE
class CONSOLE(t.CStruct):
    sht: t.CStruct(name="SHEET") | t.CPtr
    cur_x: t.CInt
    cur_y: t.CInt
    cur_c: t.CInt
    timer: t.CStruct(name="TIMER") | t.CPtr

# struct FILEHANDLE
class FILEHANDLE(t.CStruct):
    buf: t.CChar | t.CPtr
    size: t.CInt
    pos: t.CInt

# 函数声明 - void
def api33_sleep(cons: t.CStruct(name="CONSOLE") | t.CPtr, task: t.CStruct(name="TASK") | t.CPtr, time: t.CInt) -> c.State: pass
def console_task(sheet: t.CStruct(name="SHEET") | t.CPtr, memtotal: t.CInt) -> c.State: pass
def cons_putchar(cons: t.CStruct(name="CONSOLE") | t.CPtr, chr: t.CInt, move: t.CChar) -> c.State: pass
def cons_newline(cons: t.CStruct(name="CONSOLE") | t.CPtr) -> c.State: pass
def cons_putstr0(cons: t.CStruct(name="CONSOLE") | t.CPtr, s: t.CChar | t.CPtr) -> c.State: pass
def cons_putstr1(cons: t.CStruct(name="CONSOLE") | t.CPtr, s: t.CChar | t.CPtr, l: t.CInt) -> c.State: pass
def cons_runcmd(cmdline: t.CChar | t.CPtr, cons: t.CStruct(name="CONSOLE") | t.CPtr, fat: t.CInt | t.CPtr, memtotal: t.CInt) -> c.State: pass
def cmd_mem(cons: t.CStruct(name="CONSOLE") | t.CPtr, memtotal: t.CInt) -> c.State: pass
def cmd_cls(cons: t.CStruct(name="CONSOLE") | t.CPtr) -> c.State: pass
def cmd_ls(cons: t.CStruct(name="CONSOLE") | t.CPtr) -> c.State: pass
def cmd_ver(cons: t.CStruct(name="CONSOLE") | t.CPtr) -> c.State: pass
def cmd_help(cons: t.CStruct(name="CONSOLE") | t.CPtr) -> c.State: pass
def cmd_type(cons: t.CStruct(name="CONSOLE") | t.CPtr, fat: t.CInt | t.CPtr, cmdline: t.CChar | t.CPtr) -> c.State: pass
def cmd_dir(cons: t.CStruct(name="CONSOLE") | t.CPtr) -> c.State: pass
def cmd_reboot(cons: t.CStruct(name="CONSOLE") | t.CPtr) -> c.State: pass
def cmd_exit(cons: t.CStruct(name="CONSOLE") | t.CPtr, fat: t.CInt | t.CPtr) -> c.State: pass
def cmd_start(cons: t.CStruct(name="CONSOLE") | t.CPtr, cmdline: t.CChar | t.CPtr, memtotal: t.CInt) -> c.State: pass
def cmd_ncst(cons: t.CStruct(name="CONSOLE") | t.CPtr, cmdline: t.CChar | t.CPtr, memtotal: t.CInt) -> c.State: pass
# 函数声明 - int
def cmd_app(cons: t.CStruct(name="CONSOLE") | t.CPtr, fat: t.CInt | t.CPtr, cmdline: t.CChar | t.CPtr) -> t.CInt | c.State: pass
def cmd_fab(cons: t.CStruct(name="CONSOLE") | t.CPtr, fat: t.CInt | t.CPtr, cmdline: t.CChar | t.CPtr) -> c.State: pass

# 函数声明 - int*
def exw_api(edi: t.CInt, esi: t.CInt, ebp: t.CInt, esp: t.CInt, ebx: t.CInt, edx: t.CInt, ecx: t.CInt, eax: t.CInt) -> t.CInt | t.CPtr | c.State: pass
# 函数声明 - int*
def inthandler0d(esp: t.CInt | t.CPtr) -> t.CInt | t.CPtr | c.State: pass
def inthandler0c(esp: t.CInt | t.CPtr) -> t.CInt | t.CPtr | c.State: pass
# 函数声明 - void
def exw_api_linewin(sht: t.CStruct(name="SHEET") | t.CPtr, x0: t.CInt, y0: t.CInt, x1: t.CInt, y1: t.CInt, col: t.CInt) -> c.State: pass

# struct FILEINFO
class FILEINFO(t.CStruct):
    name: t.CUnsignedChar[8]
    ext: t.CUnsignedChar[3]
    type: t.CUnsignedChar
    reserve: t.CChar[10]
    time: t.CUnsignedShort
    date: t.CUnsignedShort
    clustno: t.CUnsignedShort
    size: t.CUnsignedInt

# 函数声明 - void
def file_readfat(fat: t.CInt | t.CPtr, img: t.CUnsignedChar | t.CPtr) -> c.State: pass
def file_loadfile(clustno: t.CInt, size: t.CInt, buf: t.CChar | t.CPtr, fat: t.CInt | t.CPtr, img: t.CChar | t.CPtr) -> c.State: pass
# 函数声明 - struct FILEINFO*
def file_search(name: t.CChar | t.CPtr, finfo: t.CStruct(name="FILEINFO") | t.CPtr, max: t.CInt) -> t.CStruct(name="FILEINFO") | t.CPtr | c.State: pass
# 函数声明 - char*
def file_loadfile2(clustno: t.CInt, psize: t.CInt | t.CPtr, fat: t.CInt | t.CPtr) -> t.CChar | t.CPtr | c.State: pass
# 函数声明 - int
def tek_getsize(p: t.CUnsignedChar | t.CPtr) -> t.CInt | c.State: pass
def tek_decomp(p: t.CUnsignedChar | t.CPtr, q: t.CChar | t.CPtr, size: t.CInt) -> t.CInt | c.State: pass

# 函数声明 - struct TASK*
def open_constask(sht: t.CStruct(name="SHEET") | t.CPtr, memtotal: t.CUnsignedInt) -> TASK | t.CPtr | c.State: pass
# 函数声明 - struct SHEET*
def open_console(shtctl: t.CStruct(name="SHTCTL") | t.CPtr, memtotal: t.CUnsignedInt) -> SHEET | t.CPtr | c.State: pass

# 外部全局变量
MOUSEX: t.CExtern | t.CInt = c.State
MOUSEY: t.CExtern | t.CInt = c.State
MOUSEBTN: t.CExtern | t.CInt = c.State
mousemode: t.CExtern | t.CInt = c.State
sht_back: t.CExtern | t.CStruct(name="SHEET") | t.CPtr = c.State
sht_mouse: t.CExtern | t.CStruct(name="SHEET") | t.CPtr = c.State
binfo: t.CExtern | t.CStruct(name="BOOTINFO") | t.CPtr = c.State
shtctl: t.CExtern | t.CStruct(name="SHTCTL") | t.CPtr = c.State
memtotal: t.CExtern | t.CUnsignedInt = c.State
sht_start: t.CExtern | t.CStruct(name="SHEET") | t.CPtr = c.State
buf_start: t.CExtern | t.CUnsignedChar | t.CPtr = c.State
sht_start_flan: t.CExtern | t.CInt = c.State
RegistrationCode: t.CExtern | t.CChar | t.CPtr = c.State
finfo: t.CExtern | t.CStruct(name="FILEINFO") | t.CPtr = c.State
sht: t.CExtern | t.CStruct(name="SHEET") | t.CPtr = c.State
key_win: t.CExtern | t.CStruct(name="SHEET") | t.CPtr = c.State
sht2: t.CExtern | t.CStruct(name="SHEET") | t.CPtr = c.State
fifo: t.CExtern | t.CStruct(name="FIFO32") = c.State
keycmd: t.CExtern | t.CStruct(name="FIFO32") = c.State
key_shift: t.CExtern | t.CInt = c.State
key_leds: t.CExtern | t.CInt = c.State
keycmd_wait: t.CExtern | t.CInt = c.State

KEYCMD_LED: t.CDefine = 0xed

# 静态数组
keytable0: t.CStatic | t.CChar[0x80]
keytable1: t.CStatic | t.CChar[0x80]

cmos_index: t.CDefine    = 0x70
cmos_data: t.CDefine     = 0x71
CMOS_CUR_SEC: t.CDefine  = 0x0
CMOS_ALA_SEC: t.CDefine  = 0x1
CMOS_CUR_MIN: t.CDefine  = 0x2
CMOS_ALA_MIN: t.CDefine  = 0x3
CMOS_CUR_HOUR: t.CDefine = 0x4
CMOS_ALA_HOUR: t.CDefine = 0x5
CMOS_WEEK_DAY: t.CDefine = 0x6
CMOS_MON_DAY: t.CDefine  = 0x7
CMOS_CUR_MON: t.CDefine  = 0x8
CMOS_CUR_YEAR: t.CDefine = 0x9
CMOS_DEV_TYPE: t.CDefine = 0x12
CMOS_CUR_CEN: t.CDefine  = 0x32
def BCD_HEX(n) -> t.CDefine: return ((n >> 4) * 10) + (n & 0xf)
def BCD_ASCII_first(n) -> t.CDefine: return(((n<<4)>>4)+0x30)
def BCD_ASCII_S(n) -> t.CDefine: return((n<<4)+0x30)

def get_hour_hex() -> t.CUnsignedInt | c.State: pass
def get_min_hex() -> t.CUnsignedInt | c.State: pass
def get_sec_hex() -> t.CUnsignedInt | c.State: pass
def get_day_of_month() -> t.CUnsignedInt | c.State: pass
def get_day_of_week() -> t.CUnsignedInt | c.State: pass
def get_mon_hex() -> t.CUnsignedInt | c.State: pass
def get_year() -> t.CUnsignedInt | c.State: pass

# struct ACPI_RSDP
class ACPI_RSDP(t.CStruct):
    Signature: t.CChar[8]
    Checksum: t.CUnsignedChar
    OEMID: t.CChar[6]
    Revision: t.CUnsignedChar
    RsdtAddress: t.CUnsignedInt
    Length: t.CUnsignedInt
    XsdtAddress: t.CUnsignedInt[2]
    ExtendedChecksum: t.CUnsignedChar
    Reserved: t.CUnsignedChar[3]

# struct ACPISDTHeader
class ACPISDTHeader(t.CStruct):
    Signature: t.CChar[4]
    Length: t.CUnsignedInt
    Revision: t.CUnsignedChar
    Checksum: t.CUnsignedChar
    OEMID: t.CChar[6]
    OEMTableID: t.CChar[8]
    OEMRevision: t.CUnsignedInt
    CreatorID: t.CUnsignedInt
    CreatorRevision: t.CUnsignedInt

# struct ACPI_RSDT
class ACPI_RSDT(t.CStruct):
    header: t.CStruct(name="ACPISDTHeader")
    Entry: t.CUnsignedInt

# struct GenericAddressStructure
class GenericAddressStructure(t.CStruct):
    AddressSpace: t.CUnsignedChar
    BitWidth: t.CUnsignedChar
    BitOffset: t.CUnsignedChar
    AccessSize: t.CUnsignedChar
    Address: t.CUnsignedInt[2]

# struct ACPI_FADT
class ACPI_FADT(t.CStruct):
    h: t.CStruct(name="ACPISDTHeader")
    FirmwareCtrl: t.CUnsignedInt
    Dsdt: t.CUnsignedInt
    Reserved: t.CUnsignedChar
    PreferredPowerManagementProfile: t.CUnsignedChar
    SCI_Interrupt: t.CUnsignedShort
    SMI_CommandPort: t.CUnsignedInt
    AcpiEnable: t.CUnsignedChar
    AcpiDisable: t.CUnsignedChar
    S4BIOS_REQ: t.CUnsignedChar
    PSTATE_Control: t.CUnsignedChar
    PM1aEventBlock: t.CUnsignedInt
    PM1bEventBlock: t.CUnsignedInt
    PM1aControlBlock: t.CUnsignedInt
    PM1bControlBlock: t.CUnsignedInt
    PM2ControlBlock: t.CUnsignedInt
    PMTimerBlock: t.CUnsignedInt
    GPE0Block: t.CUnsignedInt
    GPE1Block: t.CUnsignedInt
    PM1EventLength: t.CUnsignedChar
    PM1ControlLength: t.CUnsignedChar
    PM2ControlLength: t.CUnsignedChar
    PMTimerLength: t.CUnsignedChar
    GPE0Length: t.CUnsignedChar
    GPE1Length: t.CUnsignedChar
    GPE1Base: t.CUnsignedChar
    CStateControl: t.CUnsignedChar
    WorstC2Latency: t.CUnsignedShort
    WorstC3Latency: t.CUnsignedShort
    FlushSize: t.CUnsignedShort
    FlushStride: t.CUnsignedShort
    DutyOffset: t.CUnsignedChar
    DutyWidth: t.CUnsignedChar
    DayAlarm: t.CUnsignedChar
    MonthAlarm: t.CUnsignedChar
    Century: t.CUnsignedChar
    BootArchitectureFlags: t.CUnsignedShort
    Reserved2: t.CUnsignedChar
    Flags: t.CUnsignedInt
    ResetReg: t.CStruct(name="GenericAddressStructure")
    ResetValue: t.CUnsignedChar
    Reserved3: t.CUnsignedChar[3]
    X_FirmwareControl: t.CUnsignedInt[2]
    X_Dsdt: t.CUnsignedInt[2]
    X_PM1aEventBlock: t.CStruct(name="GenericAddressStructure")
    X_PM1bEventBlock: t.CStruct(name="GenericAddressStructure")
    X_PM1aControlBlock: t.CStruct(name="GenericAddressStructure")
    X_PM1bControlBlock: t.CStruct(name="GenericAddressStructure")
    X_PM2ControlBlock: t.CStruct(name="GenericAddressStructure")
    X_PMTimerBlock: t.CStruct(name="GenericAddressStructure")
    X_GPE0Block: t.CStruct(name="GenericAddressStructure")
    X_GPE1Block: t.CStruct(name="GenericAddressStructure")

# 函数声明 - void
def init_acpi() -> c.State: pass
# 函数声明 - int
def acpi_shutdown() -> t.CInt | c.State: pass

# 函数声明 - int
def win_zonclick(mdec: t.CInt, mx: t.CInt, my: t.CInt, QX: t.CInt, QY: t.CInt, SX: t.CInt, SY: t.CInt, flan: t.CInt, sht: t.CStruct(name="SHEET") | t.CPtr) -> t.CInt | c.State: pass
def win_szonclick(mdec: t.CInt, mx: t.CInt, my: t.CInt, QX: t.CInt, QY: t.CInt, SX: t.CInt, SY: t.CInt, flan: t.CInt, sht: t.CStruct(name="SHEET") | t.CPtr) -> t.CInt | c.State: pass
# 函数声明 - void
def init_start(sht: t.CStruct(name="SHEET") | t.CPtr) -> c.State: pass
def init_startlogo(b: t.CInt) -> c.State: pass
# 函数声明 - int
def binddmousebox(mx: t.CInt, my: t.CInt, mdec: t.CInt, QX: t.CInt, QY: t.CInt, EX: t.CInt, EY: t.CInt, mod: t.CInt) -> t.CInt | c.State: pass

# 宏定义
ASCLL: t.CDefine = 0
JAPANSE: t.CDefine = 1
JPEUC: t.CDefine = 2
CHINESE: t.CDefine = 3
MAX_LANGUAGE_NUMBER: t.CDefine = 10
LANGUAGE_NUMBER_NOW: t.CDefine = 4

# 外部全局数组
languages: t.CExtern | t.CInt[MAX_LANGUAGE_NUMBER] = c.State

# 函数声明 - void
def language_init() -> c.State: pass
# ================================= 原始顺序结束 =================================