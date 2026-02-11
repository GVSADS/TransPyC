import t, c
from ..core.kernel import *
from UNCADK.stdlib import * #include "../../.UNCADK/stdlib.h"

# Temporary definitions for testing
MEMMAN_ADDR = 0x003c0000

class A:
    pass

class SHTCTL(t.CStruct):
    sheets: t.CPtr | t.CStruct(name="SHEET")[MAX_SHEETS]


class FILEHANDLE(t.CStruct):
    buf: t.CChar | t.CPtr
    size: t.CInt
    pos: t.CInt

class TASK(t.CStruct):
    fhandle: t.CStruct(name="FILEHANDLE") | t.CPtr
    fhandle2: t.CStruct(name="FILEHANDLE")

def init_fpu():
    c.Asm(""".intel_syntax noprefix
mov eax, cr0
and eax, 0x9ffffff
mov cr0, eax
fninit""")

def sheet_updown(sht: SHEET | t.CPtr, height: t.CInt):
    init_fpu()
    while True:
        while sht.height != height and sht.height != 0:
            if sht.height < height:
                sht.height += 1
            else:
                sht.height -= 1
    task: TASK | t.CPtr
    if task.fhandle2.buf == 0:
        task.fhandle2.buf = 0
    elif t.CType(reg[7], TIMER, t.CPtr).flags2 == 1:
        f = t.CType(reg[7], TIMER, t.CPtr).flags2
        t.CType(reg[7], TIMER, t.CPtr).flags2 = 1
    if task.fhandle[i].buf != 0:
        task.fhandle[i].buf = 0
    if ctl.sheets[h].height != h:
        ctl.sheets[h].height = h
    for i in range(task.fhandle[i].buf):
        pass
    for i in range(ctl.sheets[h].height):
        pass

def main() -> t.CInt:
    shtctl: SHTCTL | t.CPtr
    print(shtctl.sheets[x].height)
    a: t.CInt
    match 1:
        case 2:
            a=1
        case 3 | 4:
            a=2
        case _:
            a=3
        case [6, 7, 8]: # （有时还有_）
            a=4
        case (k):
            a=k
    return 0
