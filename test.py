import c
import t
# 导入标准库
import stdio  # std: standard
from kernel2 import *


F1: t.CDefine = -1
def keywin_off(key_win: t.CStruct(name="SHEET") | t.CPtr) -> c.State | t.CVoid: pass
def keywin_off2(key_win: t.CPtr | t.CStruct(name="SHEET")) -> c.State: pass

MOUSEX: t.CInt

# 测试数组声明
keytable0: t.CStatic | t.CChar[0x80]
buf_start: t.CUnsigned | t.CChar | t.CPtr

def io_hlt() -> c.State: pass

# 测试指针操作
def test_ptr_operations():
    # 测试指针赋值
    c.Ptr(0x1000, 42)
    # 测试带类型转换的指针赋值
    c.Ptr(0x1000, 42, type=t.CInt())
    # 测试指针取值
    value = c.Ptr(0x1000)
    # 测试带类型转换的指针取值
    value = c.Ptr(0x1000, type=t.CInt())
    # 表示 struct xxx * 类型
    var: t.CStruct | t.CPtr = value
    var2: t.CStruct | t.CPtr = value()


# 测试类型转换
def test_type_casting():
    x = 42
    # 测试简单类型转换
    y = t.CType(x, t.CInt())
    z: t.CChar = t.CType(x, t.CChar())
    # 测试组合类型转换
    p = t.CType(x, t.CUnsigned(), t.CChar(), t.CPtr())
    # 测试单个类型转换函数
    q = t.CInt(x)
    r = t.CChar(x)
    
    if x:
        x = t.CType(x, t.CInt())
        if x:
            x = t.CType(x, t.CInt())
    if x:
        x = t.CInt(x)

# 测试变量声明和类型注解
global_var: t.CInt = 100
static_var: t.CStatic | t.CInt = 200
# 测试冒泡排序
def test_bubble_sort() -> t.CLong | t.CInt:
    # 定义一个数组
    arr: t.CLong | t.CInt[7] = [64, 34, 25, 12, 22, 11, 90]
    n = len(arr)
    
    # 冒泡排序算法
    for i in range(n):
        # 最后i个元素已经就位
        for j in range(0, n-i-1):
            # 遍历数组，比较相邻元素
            if arr[j] > arr[j+1]:
                # 交换元素
                arr[j], arr[j+1] = arr[j+1], arr[j]
    
    # 打印排序后的数组
    print("排序后的数组:")
    for i in range(n):
        print(arr[i])
    return arr

class a:
    k1: t.CInt
    task: t.CStruct | t.CPtr = TASK
    def __init__(self, led: t.CInt = 0):
        self.led: t.CInt = led
    def add(self, x: t.CInt) -> t.CInt:
        self.led += x
        return self.led
    # 测试冒泡排序
    def test_bubble_sort(self):
        # 定义一个数组
        arr: t.CLong | t.CInt[7] = [64, 34, 25, 12, 22, 11, 90]
        n = len(arr)
        
        # 冒泡排序算法
        for i in range(n):
            # 最后i个元素已经就位
            for j in range(0, n-i-1):
                # 遍历数组，比较相邻元素
                if arr[j] > arr[j+1]:
                    # 交换元素
                    arr[j], arr[j+1] = arr[j+1], arr[j]
        
        # 打印排序后的数组
        print("排序后的数组:")
        for i in range(n):
            print(arr[i])

def io_out8(port: t.CUInt8T, value: t.CUInt8T):
    c.Asm("out %0, %1" % (value, port))

class DLL_STRPICENV(t.CStruct):
    work: t.CInt[64 * 1024 // 4]
    free: t.CPtr | FREEINFO[MEMMAN_FREES] = c.State
    sheets: t.CPtr | t.CStruct | SHEET[MAX_SHEETS] = c.State
    sheets: t.CPtr | SHEET[MAX_SHEETS] = c.State
    sheets0: t.CStruct | SHEET[MAX_SHEETS] = c.State
taskctl: t.CExtern | t.CPtr | TASKCTL = c.State
task_timer: TIMER | t.CExtern | t.CPtr = c.State


def open_constask(sht: t.CPtr | SHEET, memtotal: t.CUnsignedInt) -> c.State | t.CStruct(name=TASK) | t.CPtr: pass
def open_constask2(sht: t.CPtr | SHEET, memtotal: t.CUnsignedInt) -> c.State | t.CStruct(name=TASK): pass

def info_JPEG(env: t.CPtr | DLL_STRPICENV, info: t.CPtr | t.CInt, size: t.CInt, fp: t.CPtr | t.CUInt8T) -> t.CInt | c.State: pass

def memman_free_4k(man: t.CPtr | t.CStruct | MEMMAN, addr: t.CUnsignedInt, size: t.CUnsignedInt) -> c.State: pass

def sheet_setbuf(sht: t.CPtr | t.CStruct | SHEET, buf: t.CPtr | t.CUnsignedChar, xsize: t.CInt, ysize: t.CInt, col_inv: t.CInt) -> c.State: pass

languages: t.CExtern | t.CInt[MAX_LANGUAGE_NUMBER] = c.State

sht_mouse: t.CPtr | SHEET
shtctl: t.CPtr | SHTCTL

keytable0: t.CStatic | t.CChar[0x80] = [
	0,   0,   '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', 0x08,   0,
	'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '[', ']', 0x0a,   0,   'A', 'S',
	'D', 'F', 'G', 'H', 'J', 'K', 'L', ';', "'", '`',   0,   '\\', 'Z', 'X', 'C', 'V',
	'B', 'N', 'M', ',', '.', '/', 0,   '*', 0,   ' ', 0,   0,   0,   0,   0,   0,
	0,   0,   0,   0,   0,   0,   0,   '7', 0, '9', '-', '4', '5', '6', '+', '1',
	0, '3', '0', '.', 0,	 0,   0,    0,    0,   0, 0,   0,    0,  0,   0,    0,
		0,   0,   0,  0,   0,	 0,   0,    0,    0,   0, 0,   0,    0,  0,   0,    0,
		0,   0,   0,  0x5c, 0,	 0,   0,    0,    0,   0, 0,   0,    0,  0x5c, 0,    0,
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



class FIFO32: pass

f: FIFO32
binfo: t.CPtr | BOOTINFO = t.CType(ADR_BOOTINFO, BOOTINFO, t.CPtr)

finfo: t.CPtr | FILEINFO
def main() -> t.CInt:
    c.Ptr(0xec, t.CInt(c.Addr(X)), type=t.CInt | t.CLong)
    cons_fifo: t.CInt | t.CPtr = 1
    cons_fifo2: t.CLong | t.CInt = 1
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

    finfo = file_search("HZK16.fnt", t.CType((ADR_DISKIMG + 0x002600), FILEINFO, t.CPtr), 224)
    init_start(sht_start)
    file_loadfile(t.CType((ADR_DISKIMG + 0x003e00), t.CChar, t.CPtr))
    file_loadfile(t.CChar((ADR_DISKIMG + 0x003e00, t.CPtr)))

    buf_start = t.CType(memman_alloc_4k(memman, 450 * 600), t.CUnsignedChar, t.CPtr)
    shtctl = shtctl_init(memman, binfo.vram, binfo.scrnx, binfo.scrny)
    keytable0: t.CStatic | t.CChar[0x80] = c.State
    keytable1: t.CStatic | t.CChar[0x80] = c.State
    font1: t.CExtern | t.CChar[4096]
    buf_back: t.CUnsigned | t.CChar | t.CPtr
    buf_mouse: t.CUnsigned | t.CChar[256][256] | t.CPtr

    memtotal = memtest(0x00400000, 0xbfffffff)

    fifo: FIFO32
    fifo.task = task_a

    key_leds = (binfo.leds >> 4) & 7

    # 调用冒泡排序测试
    K = test_bubble_sort()

    s = a(1)
    p: t.CStruct | t.CPtr | a = a
    p = c.Addr(s)
    s.test_bubble_sort(s.k1, p.k1)

    c.Ptr(0x0fec, t.CInt(c.Addr(fifo)), type=t.CInt)
    io_out8(PIC1_IMR, 0x00400000)
    p.flags |= 0x20
    key_win = shtctl.sheets[shtctl.top - 1]
    key_shift &= ~1

    return 0
