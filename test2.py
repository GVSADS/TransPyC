import t, c

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