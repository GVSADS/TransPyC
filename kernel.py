from kernel2 import * # std: standard
import stdio # std: standard
import string # std: standard
import c, t


F1: t.CDefine = -1
F2: t.CDefine = -2
F3: t.CDefine = -3
F4: t.CDefine = -4
F5: t.CDefine = -5
F6: t.CDefine = -6
F7: t.CDefine = -7
F8: t.CDefine = -8
F9: t.CDefine = -9
F10: t.CDefine = -10
F11: t.CDefine = -11
F12: t.CDefine = -12
ESC: t.CDefine = -350
BCK: t.CDefine = 0x08
TAB: t.CDefine = 0x09
LSH: t.CDefine = -158
LCT: t.CDefine = -187
LAL: t.CDefine = -141
FXU: t.CDefine = -111
FXD: t.CDefine = -112
FXL: t.CDefine = -113
FXR: t.CDefine = -114
XEN: t.CDefine = -120
RCT: t.CDefine = -121
XXG: t.CDefine = -122
RSH: t.CDefine = -123
RAL: t.CDefine = -124
HME: t.CDefine = -125
PGU: t.CDefine = -126
END: t.CDefine = -127
PGD: t.CDefine = -128
INS: t.CDefine = -129
DEL: t.CDefine = -130
WIN: t.CDefine = -131
RMN: t.CDefine = -132

def keywin_off(key_win: t.CPtr | t.CStruct(name="SHEET")) -> c.State: pass
def keywin_on(key_win: t.CPtr | t.CStruct(name="SHEET")) -> c.State: pass
def close_console(sht: t.CPtr | t.CStruct(name="SHEET")) -> c.State: pass
def close_constask(task: t.CPtr | t.CStruct(name="TASK")) -> c.State: pass
MOUSEX: t.CInt
MOUSEY: t.CInt
MOUSEBTN: t.CInt
sht_back: t.CPtr | SHEET
sht_mouse: t.CPtr | SHEET
shtctl: t.CPtr | SHTCTL
memtotal: t.CUnsignedInt
binfo: t.CPtr | BOOTINFO = t.CType(ADR_BOOTINFO, BOOTINFO, t.CPtr)

sht_start: t.CPtr | SHEET
buf_start: t.CUnsignedChar
sht_start_flan: t.CInt = 0
RegistrationCode: t.CChar | t.CPtr = "0x000001"
finfo: t.CPtr | FILEINFO
sht: t.CPtr | SHEET = 0
key_win: t.CPtr | SHEET
sht2: t.CPtr | SHEET
fifo: FIFO32
keycmd: FIFO32
key_shift: t.CInt = 0
key_leds: t.CInt = 0
keycmd_wait: t.CInt = -1
imewords: t.CChar | t.CPtr

memman: t.CPtr | MEMMAN = t.CType(MEMMAN_ADDR, MEMMAN, t.CPtr)
fat: t.CInt | t.CPtr
i: t.CInt
pxdeep: t.CInt = 16
Input_method: t.CInt = 0
mousemode: t.CInt = 3

keytable0: t.CStatic | t.CChar[0x80] = [
    0,   0,   '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', 0x08,   0,
    'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '[', ']', 0x0a,   0,   'A', 'S',
    'D', 'F', 'G', 'H', 'J', 'K', 'L', ';', '\'', '`',   0,   '\\', 'Z', 'X', 'C', 'V',
    'B', 'N', 'M', ',', '.', '/', 0,   '*', 0,   ' ', 0,   0,   0,   0,   0,   0,
    0,   0,   0,   0,   0,   0,   0,   '7', 0, '9', '-', '4', '5', '6', '+', '1',
    0, '3', '0', '.', 0,     0,   0,    0,    0,   0, 0,   0,    0,  0,   0,    0,
        0,   0,   0,  0,   0,     0,   0,    0,    0,   0, 0,   0,    0,  0,   0,    0,
        0,   0,   0,  0x5c, 0,     0,   0,    0,    0,   0, 0,   0,    0,  0x5c, 0,    0,
]
keytable1: t.CStatic | t.CChar[0x80] = [
    0,   0,   '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '_', '+', 0x08,   0,
    'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '{', '}', 0x0a,   0,   'A', 'S',
    'D', 'F', 'G', 'H', 'J', 'K', 'L', ':', '"', '~',   0,   '|', 'Z', 'X', 'C', 'V',
    'B', 'N', 'M', '<', '>', '?', 0,   '*', 0,   ' ', 0,   0,   0,   0,   0,   0,
    0,   0,   0,   0,   0,   0,   0,   '7', '8', '9', '-', '4', '5', '6', '+', '1',
    '2', '3', '0', '.', 0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
    0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
    0,   0,   0,   '_', 0,   0,   0,   0,   0,   0,   0,   0,   0,   '|', 0,   0
]

def SAIBMain():
    j: t.CInt
    x: t.CInt
    y: t.CInt
    mmx: t.CInt = -1
    mmy: t.CInt = -1
    mmx2: t.CInt = 0
    cmd: t.CPtr | SHEET
    timer_systime: t.CPtr | TIMER
    start_d: t.CPtr | TIMER
    font: t.CExtern | t.CChar[4096]
    s: t.CChar[40]
    fifobuf: t.CInt[128]
    keycmd_buf: t.CInt[32]
    mx: t.CInt
    my: t.CInt
    i: t.CInt
    new_mx: t.CInt = -1
    new_my: t.CInt = 0
    new_wx: t.CInt = 0x7fffffff
    new_wy: t.CInt = 0
    mdec: MOUSE_DEC
    buf_back: t.CUnsignedChar | t.CPtr
    buf_mouse: t.CUnsignedChar[256]

    key_shift = 0
    key_leds = (binfo.leds >> 4) & 7
    keycmd_wait = -1

    task_a: t.CPtr | TASK
    task: t.CPtr | TASK

    nihongo: t.CUnsignedChar | t.CPtr

    init_gdtidt()
    init_pic()
    io_sti()
    fifo32_init(c.Addr(fifo), 128, fifobuf, 0)

    c.Ptr(0x0fec, t.CInt(c.Addr(fifo)), type=t.CInt)

    init_pit()
    init_keyboard(c.Addr(fifo), 256)
    enable_mouse(c.Addr(fifo), 512, c.Addr(mdec))
    io_out8(PIC0_IMR, 0xf8)
    io_out8(PIC1_IMR, 0xef)
    fifo32_init(c.Addr(keycmd), 32, keycmd_buf, 0)
    init_acpi()

    memtotal = memtest(0x00400000, 0xbfffffff)
    memman_init(memman)
    memman_free(memman, 0x00001000, 0x0009e000)
    memman_free(memman, 0x00400000, memtotal - 0x00400000)
    init_color()

    shtctl = shtctl_init(memman, binfo.vram, binfo.scrnx, binfo.scrny)
    task_a = task_init(memman)
    fifo.task = task_a
    task_run(task_a, 1, 2)
    c.Ptr(0x0fe4, t.CInt(shtctl), type=t.CInt)
    task_a.langmode = 0
    timer_systime = timer_alloc()

    timer_init(timer_systime, c.Addr(fifo), 100)
    timer_settime(timer_systime, 100)
    sht_back  = sheet_alloc(shtctl)
    buf_back  = t.CType(memman_alloc_4k(memman, binfo.scrnx * binfo.scrny), t.CUnsignedChar, t.CPtr)
    sheet_setbuf(sht_back, buf_back, binfo.scrnx, binfo.scrny, -1)
    init_desktop(buf_back, binfo.scrnx, binfo.scrny)
    sht_start = sheet_alloc(shtctl)
    buf_start = t.CType(memman_alloc_4k(memman, 450 * 600), t.CUnsignedChar, t.CPtr)
    sheet_setbuf(sht_start, buf_start, 450, 600, -1)
    init_start(sht_start)
    sheet_slide(sht_start, 0, binfo.scrny - 630)
    key_win = open_console(shtctl, memtotal)
    cmd     = key_win
    sht_mouse = sheet_alloc(shtctl)
    sheet_setbuf(sht_mouse, buf_mouse, 16, 16, 99)
    init_mouse_cursor8(buf_mouse, 99)
    mx = (binfo.scrnx - 16) / 2
    my = (binfo.scrny - 28 - 16) / 2
    sheet_slide(sht_back,  0,  0)
    sheet_slide(key_win,   32, 4)
    sheet_slide(sht_mouse, MOUSEX, MOUSEY)
    sheet_updown(sht_back,  0)
    sheet_updown(key_win,   2)
    sheet_updown(sht_mouse, 3)
    keywin_on(key_win)
    fifo32_put(c.Addr(keycmd), KEYCMD_LED)
    fifo32_put(c.Addr(keycmd), key_leds)
    nihongo = t.CType(memman_alloc_4k(memman, 0x5d5d * 32), t.CUnsignedChar, t.CPtr)
    fat = t.CType(memman_alloc_4k(memman, 4 * 2880), t.CInt, t.CPtr)
    file_readfat(fat, t.CType((ADR_DISKIMG + 0x000200), t.CUnsignedChar, t.CPtr))
    finfo = file_search("HZK16.fnt", t.CType((ADR_DISKIMG + 0x002600), FILEINFO, t.CPtr), 224)

    if finfo != 0:
        file_loadfile(finfo.clustno, finfo.size, nihongo, fat, t.CType((ADR_DISKIMG + 0x003e00), t.CChar, t.CPtr))
    else:
        for i in range(16 * 256):
            nihongo[i] = font[i]
        for i in range(16 * 256, 16 * 256 + 32 * 94 * 47):
            nihongo[i] = 0xff

    c.Ptr(0x0fe8, t.CInt(nihongo), type=t.CInt)
    memman_free_4k(memman, t.CInt(fat), 4 * 2880)
    while True:
        if fifo32_status(c.Addr(keycmd)) > 0 and keycmd_wait < 0:
            keycmd_wait = fifo32_get(c.Addr(keycmd))
            wait_KBC_sendready()
            io_out8(PORT_KEYDAT, keycmd_wait)
        io_cli()
        if fifo32_status(c.Addr(fifo)) == 0:
            if new_mx >= 0:
                io_sti()
                sheet_slide(sht_mouse, new_mx, new_my)
                new_mx = -1
            elif new_wx != 0x7fffffff:
                io_sti()
                sheet_slide(sht, new_wx, new_wy)
                new_wx = 0x7fffffff
            else:
                task_sleep(task_a)
                io_sti()
        else:
            i = fifo32_get(c.Addr(fifo))
            j = fifo.buf[(fifo.q-2 + fifo.size) % fifo.size]
            io_sti()
            if key_win != 0 and key_win.flags == 0:
                if shtctl.top == 1:
                    key_win = 0
                else:
                    key_win = shtctl.sheets[shtctl.top - 1]
                    keywin_on(key_win)
            if 256 <= i and i <= 511:
                if i < 0x80 + 256:
                    if key_shift == 0:
                        s[0] = keytable0[i - 256]
                    else:
                        s[0] = keytable1[i - 256]
                else:
                    s[0] = 0
                if 'A' <= s[0] and s[0] <= 'Z':
                    if (((key_leds & 4) == 0 and key_shift == 0) or
                            ((key_leds & 4) != 0 and key_shift != 0)):
                        s[0] += 0x20
                if s[0] != 0 and key_win != 0:
                    fifo32_put(c.Addr(key_win.task.fifo), s[0] + 256)
                if i == 256 + 0x0f and key_win != 0:
                    keywin_off(key_win)
                    j = key_win.height - 1
                    if j == 0:
                        j = shtctl.top - 1
                    key_win = shtctl.sheets[j]
                    keywin_on(key_win)
                if i == 256 + 0x63:
                    key_shift |= 2
                if i == 256 + 0x2a:
                    key_shift |= 1
                if i == 256 + 0x36:
                    key_shift |= 2
                if i == 256 + 0xaa:
                    key_shift &= ~1
                if i == 256 + 0xb6:
                    key_shift &= ~2
                if i == 256 + 0x3a:
                    key_leds ^= 4
                    fifo32_put(c.Addr(keycmd), KEYCMD_LED)
                    fifo32_put(c.Addr(keycmd), key_leds)
                if i == 256 + 0x45:
                    key_leds ^= 2
                    fifo32_put(c.Addr(keycmd), KEYCMD_LED)
                    fifo32_put(c.Addr(keycmd), key_leds)
                if i == 256 + 0x46:
                    key_leds ^= 1
                    fifo32_put(c.Addr(keycmd), KEYCMD_LED)
                    fifo32_put(c.Addr(keycmd), key_leds)
                if i == 256 + 0x3b and key_shift != 0 and key_win != 0:
                    task = key_win.task
                    if task != 0 and task.tss.ss0 != 0:
                        cons_putstr0(task.cons, "")
                        io_cli()
                        task.tss.eax = t.CInt(c.Addr(task.tss.esp0))
                        task.tss.eip = t.CInt(asm_end_app)
                        io_sti()
                        task_run(task, -1, 0)
                if i == 256 + 0x3c and key_shift != 0:
                    if key_win != 0:
                        keywin_off(key_win)
                    key_win = open_console(shtctl, memtotal)
                    sheet_slide(key_win, 32, 4)
                    sheet_updown(key_win, shtctl.top)
                    keywin_on(key_win)
                if i == 256 + 0x57:
                    sheet_updown(shtctl.sheets[1], shtctl.top - 1)
                if i == 256 + 0xfa:
                    keycmd_wait = -1
                if i == 256 + 0xfe:
                    wait_KBC_sendready()
                    io_out8(PORT_KEYDAT, keycmd_wait)
            elif 512 <= i and i <= 767:
                if mouse_decode(c.Addr(mdec), i - 512) != 0:
                    mx += mdec.x
                    my += mdec.y
                    if mx < 0:
                        mx = 0
                    if my < 0:
                        my = 0
                    if mx > binfo.scrnx - 1:
                        mx = binfo.scrnx - 1
                    if my > binfo.scrny - 1:
                        my = binfo.scrny - 1
                    new_mx = mx
                    new_my = my
                    MOUSEX = mx
                    MOUSEY = my
                    MOUSEBTN = mdec.btn
                    win_zonclick(MOUSEBTN,MOUSEX,MOUSEY,0,binfo.scrny-30,30,binfo.scrny,sht_start_flan, sht)
                    sht_start_flan = win_szonclick(MOUSEBTN,MOUSEX,MOUSEY,0,binfo.scrny-30,30,binfo.scrny,sht_start_flan, sht)
                    if (sht_start_flan == 1 and
                        ( binddmousebox(MOUSEX,MOUSEY,MOUSEBTN,0,0,binfo.scrnx,binfo.scrny-630,1) or
                        binddmousebox(MOUSEX,MOUSEY,MOUSEBTN,400,binfo.scrny-630,binfo.scrnx,binfo.scrny,1) or
                        binddmousebox(MOUSEX,MOUSEY,MOUSEBTN,30,binfo.scrny-30,400,binfo.scrny,1) or
                        binddmousebox(MOUSEX,MOUSEY,MOUSEBTN,0,0,binfo.scrnx,binfo.scrny-630,2) or
                        binddmousebox(MOUSEX,MOUSEY,MOUSEBTN,400,binfo.scrny-630,binfo.scrnx,binfo.scrny,2) or
                        binddmousebox(MOUSEX,MOUSEY,MOUSEBTN,30,binfo.scrny-30,400,binfo.scrny,2) )
                        ):
                        sheet_updown(sht_start, -1)
                        sht_start_flan = 0
                    if (mdec.btn & 0x01) != 0:
                        if mmx < 0:
                            for j in range(shtctl.top - 1, 0, -1):
                                sht = shtctl.sheets[j]
                                x = mx - sht.vx0
                                y = my - sht.vy0
                                if 0 <= x and x < sht.bxsize and 0 <= y and y < sht.bysize:
                                        sheet_updown(sht, shtctl.top - 1)
                                        if sht != key_win:
                                            keywin_off(key_win)
                                            key_win = sht
                                            keywin_on(key_win)
                                        if 3 <= x and x < sht.bxsize - 3 and 3 <= y and y < 21:
                                            mmx = mx
                                            mmy = my
                                            mmx2 = sht.vx0
                                            new_wy = sht.vy0
                                        if sht.bxsize - 21 <= x and x < sht.bxsize - 5 and 5 <= y and y < 19:
                                            if (sht.flags & 0x10) != 0:
                                                task = sht.task
                                                cons_putstr0(task.cons, "")
                                                io_cli()
                                                task.tss.eax = t.CInt(c.Addr(task.tss.esp0))
                                                task.tss.eip = t.CInt(asm_end_app)
                                                io_sti()
                                                task_run(task, -1, 0)
                                            elif sht.flags == 0x25:
                                                pass
                                            else:
                                                task = sht.task
                                                sheet_updown(sht, -1)
                                                keywin_off(key_win)
                                                key_win = shtctl.sheets[shtctl.top - 1]
                                                keywin_on(key_win)
                                                io_cli()
                                                fifo32_put(c.Addr(task.fifo), 4)
                                                io_sti()
                                        break
                        else:
                            x = mx - mmx
                            y = my - mmy
                            new_wx = (mmx2 + x + 2) & ~3
                            new_wy = new_wy + y
                            mmy = my
                    else:
                        mmx = -1
                        if new_wx != 0x7fffffff:
                            sheet_slide(sht, new_wx, new_wy)
                            new_wx = 0x7fffffff
            elif 768 <= i and i <= 1023:
                close_console(shtctl.sheets0 + (i - 768))
            elif 1024 <= i and i <= 2023:
                close_constask(taskctl.tasks0 + (i - 1024))
            elif 2024 <= i and i <= 2279:
                sht2 = shtctl.sheets0 + (i - 2024)
                memman_free_4k(memman, t.CInt(sht2.buf), 256 * 165)
                sheet_free(sht2)
            elif i == 100:
                sprintf(s, "%d/%d/%d", get_year(), get_mon_hex(), get_day_of_month())
                putfonts8_asc_sht(sht_back, binfo.scrnx - 170, binfo.scrny -20, COL8_FFFFFF, COL8_RWL, s, 15)
                sprintf(s, "%d:%d:%d", get_hour_hex(), get_min_hex(), get_sec_hex())
                putfonts8_asc_sht(sht_back, binfo.scrnx - 70, binfo.scrny -20, COL8_FFFFFF, COL8_RWL, s, 8)
                sheet_refresh(sht_back, binfo.scrnx - 200, binfo.scrny -20,binfo.scrnx - 70 + 5*8, binfo.scrny -50+16)
                timer_settime(timer_systime, 100)

def keywin_off(key_win: SHEET | t.CPtr):
    change_wtitle8(key_win, 0)
    if (key_win.flags & 0x20) != 0:
        fifo32_put(c.Addr(key_win.task.fifo), 3)
    return

def keywin_on(key_win: SHEET | t.CPtr):
    change_wtitle8(key_win, 1)
    if (key_win.flags & 0x20) != 0:
        fifo32_put(c.Addr(key_win.task.fifo), 2)
        fifo32_put(c.Addr(key_win.task2.fifo), 2)
    return

def open_constask(sht: SHEET | t.CPtr, memtotal: t.CUnsignedInt) -> t.CPtr | TASK:
    memman: MEMMAN | t.CPtr = t.CStruct(MEMMAN_ADDR, MEMMAN, t.CPtr)
    task: TASK | t.CPtr = task_alloc()
    cons_fifo: t.CInt | t.CPtr = t.CInt(memman_alloc_4k(memman, 128 * 4), t.CPtr)
    task.cons_stack = memman_alloc_4k(memman, 64 * 1024)
    task.tss.esp = task.cons_stack + 64 * 1024 - 12
    task.tss.eip = t.CInt(c.Addr(console_task))
    task.tss.es = 1 * 8
    task.tss.cs = 2 * 8
    task.tss.ss = 1 * 8
    task.tss.ds = 1 * 8
    task.tss.fs = 1 * 8
    task.tss.gs = 1 * 8
    c.Ptr(task.tss.esp + 4, t.CInt(sht), type=t.CInt)
    c.Ptr(task.tss.esp + 8, memtotal,    type=t.CInt)
    task_run(task, 2, 2)
    fifo32_init(c.Addr(task.fifo), 128, cons_fifo, task)
    return task

cmdico: t.CInt[16][16] = [
  [7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7],
  [15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,7,7,7,0,7,0,7,0,0,0,0,0,0,0,0],
  [0,7,0,0,0,0,0,0,7,0,0,0,0,0,0,0],
  [0,7,7,7,0,7,0,0,0,7,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7]
]

def open_console(shtctl: SHTCTL | t.CPtr, memtotal: t.CUnsignedInt) -> SHEET | t.CPtr:
    i: t.CInt = 0
    j: t.CInt = 0
    memman: MEMMAN | t.CPtr = t.CType(MEMMAN_ADDR, MEMMAN, t.CPtr)
    sht: SHEET | t.CPtr = sheet_alloc(shtctl)
    buf: t.CUnsignedChar | t.CPtr = t.CUnsignedChar(memman_alloc_4k(memman, 525 * 479), t.CPtr)
    sheet_setbuf(sht, buf, 525, 479, 255)
    make_window8(buf, 525, 479, "Cmd.exw(System Internal storage)", 0)
    make_textbox8(sht, 3, 24, 519, 452, COL8_000000)
    for i in range(16):
        for j in range(16):
            buf[(i+4)*525 + j + 6] = cmdico[i][j]
    sht.task = open_constask(sht, memtotal)
    sht.flags |= 0x20
    return sht

def close_constask(task: TASK | t.CPtr):
    memman: MEMMAN | t.CPtr = t.CType(MEMMAN_ADDR, MEMMAN, t.CPtr)
    task_sleep(task)
    memman_free_4k(memman, task.cons_stack, 64 * 1024)
    memman_free_4k(memman, t.CInt(task.fifo.buf), 525 * 4)
    task.flags = 0
    return

def close_console(sht: SHEET | t.CPtr):
    memman: MEMMAN | t.CPtr = t.CType(MEMMAN_ADDR, MEMMAN, t.CPtr)
    task: TASK | t.CPtr = sht.task
    memman_free_4k(memman, t.CInt(sht.buf), 770 * 655)
    sheet_free(sht)
    close_constask(task)
    return
