def bytes(s):
    bs = []
    while len(s) > 0:
        xx = s[:2]
        s = s[2:]
        bs.append(int(xx, 16))
    return bs
    
constTypes = ["None", "Utf8", "None", "Integer", "Float", "Long", "Double", "Class", "String", "Fieldref", "Methodref", "InterfaceMethodRef", "NameAndType"]

class Bytes:
    def __init__(self, bytes):
        self.bytes = bytes
        self.index = 0
        self.lineNumbers = []
        
    def skip(self, n):
        self.index = self.index + n
        
    def u1(self):
        b = self.bytes[self.index]
        self.skip(1)
        return b        
        
    def u2(self):
        bs = self.bytes[self.index:self.index+2]
        self.skip(2)
        return bs[0] * 256 + bs[1]
    
    def u4(self):
        bs = self.bytes[self.index:self.index+4]
        self.skip(4)
        return ((bs[0] * 256 + bs[1]) * 256 + bs[2]) * 256 + bs[3]
        
    def getUTF(self):
        length = self.u2()
        s = "".join([chr(c) for c in self.bytes[self.index:self.index+length]])        
        if s.startswith("$Id") and s.endswith("$"):
            self.bytes[self.index-2:self.index+length] = []
            self.skip(-2)
        else:    
            self.skip(length)
        return s
        
    def lineNumber(self):
        self.lineNumbers.append(self.index)
        return self.u2()
        
    def patchLineNumbers(self):
        #print "Patching %d line numbers" % len(self.lineNumbers)
        for ln in self.lineNumbers:
            self.bytes[ln] = 0
            self.bytes[ln+1] = 0        
        
def getCode(bytes, constants):
    maxStack = bytes.u2()
    maxLocals = bytes.u2()
    codeLen = bytes.u4()
    bytes.skip(codeLen)
    etLen = bytes.u2()
    for i in range(etLen):
        bytes.skip(8)
    getAttributes(bytes, constants)       
    
def getLineNumberTable(bytes, constants):
    length = bytes.u2()
    for i in range(length):
        bytes.skip(2)
        ln = bytes.lineNumber()
    
def getAttributes(bytes, constants):
    aCount = bytes.u2()
    for j in range(aCount):
        anIndex = bytes.u2()
        atLen = bytes.u4()
        if constants[anIndex] == "Code":
            getCode(bytes, constants)
        elif constants[anIndex] == "LineNumberTable":
            getLineNumberTable(bytes, constants)
        else:
            bytes.skip(atLen)
    
def nullLineNumbers(bytes):
    bytes = Bytes(bytes)
    bytes.skip(8)
    cpCount = bytes.u2()
    i = 1
    constants = {}
    while i < cpCount:
        type = bytes.u1()
        if type in [9, 10, 11]:
            bytes.skip(4)
        elif type == 12:
            bytes.skip(4)
        elif type == 7:
            bytes.skip(2)
        elif type == 8:
            bytes.skip(2)         
        elif type in [5, 6]:
            bytes.skip(8)
        elif type in [3, 4]:
            bytes.skip(4)
        elif type == 1:
            constants[i] = bytes.getUTF()
        i = i + 1
        if type in [5,6]:
            i = i + 1
    bytes.skip(6)
    iCount = bytes.u2()
    for i in range(iCount):
        ii = bytes.u2()
    fCount = bytes.u2()
    for i in range(fCount):
        bytes.skip(6)
        getAttributes(bytes, constants)
    mCount = bytes.u2()
    for i in range(mCount):
        bytes.skip(6)
        getAttributes(bytes, constants)        
    getAttributes(bytes, constants)
    bytes.patchLineNumbers()
    return bytes.bytes
