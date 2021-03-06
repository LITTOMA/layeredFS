import sys
import os
import glob
import struct
import filecmp
import shutil

code = '';
addrdb = {};
base = 0x00100000;

def findNearestSTMFD(code, pos):
	pos = (pos // 4) * 4;
	term = pos - 0x1000;
	if term < 0:
		term = 0;
	while (pos >= term) :
		if (code[pos + 2: pos + 4] == '\x2d\xe9'):
			return pos;
		pos -= 4;
	return 0;
	
def findFunction(code, sig):
	global base;
	
	t = code.find(sig);
	if (t == -1):
		return 0;
	return base + findNearestSTMFD(code, t);

def save(k, v):
	global addrdb, base;
	if (not addrdb.has_key(k)):
		addrdb[k] = '0';
	if (v != 0):
		addrdb[k] = hex(v);

def findAll(code, sig):
	r = [];
	off = 0;
	while True:
		t = code.find(sig, off);
		if (t == -1):
			return r;
		off = t + 1;
		r.append(t);

def parseHexStr(s):
	t = '';
	for i in s.split(' '):
		if (len(i) > 0): 
			t += chr(int('0x' + i, 0));
	return t;

def locateHid():
	global code, base;
	
	save('hidObj', 0);
	t = code.find('hid:USER');
	if (t == -1):
		print('strHidUser not found');
		return;
	strHidUser =  t + base;
	print('strHidUser: %08x' % strHidUser);
	
	t = code.find(struct.pack('I', strHidUser));
	if (t == -1):
		print('refHidUser not found');
		return;
	refHidUser =  t + base;
	print('refHidUser: %08x' % refHidUser);
	
	r = findAll(code, struct.pack('I', refHidUser - 8));
	hidObj = 0;
	for i in r:
		(t,) = struct.unpack('I', code[i + 4: i + 8]);	
		if ((t & 0x80000000) == 0):
			hidObj = t;

	print('hidObj: %08x' % hidObj);
	
	save('hidObj', hidObj);

def locateFS() :
	global code, base;
	save('fsUserHandle', 0);
	save('fsOpenFile', findFunction(code, parseHexStr('c2 01 02 08')));
	save('fsOpenArchive', findFunction(code, parseHexStr('c2 00 0c 08')));
	save('fsWriteFile', findFunction(code, parseHexStr('02 01 03 08')));
	t = code.find(parseHexStr('f9 67 a0 08'));
	if (t == 0):
		return;
	(fsUserHandle,) = struct.unpack('I', code[t - 4: t]);
	save('fsUserHandle', fsUserHandle);

def walk(dirname):
                filelist = []
                for root,dirs,files in os.walk(dirname):
                                for filename in files:
                                                fullname=os.path.join(root,filename)
                                                filelist.append(fullname)
                return filelist

def cmpfile(fn1,fn2):
                f1 = open(fn1,'rb')
                f2 = open(fn2,'rb')
                d1 = f1.read()
                d2 = f2.read()
                f1.close()
                f2.close()
                if d1==d2:
                                return False
                else:
                                return d2
def mkdir(path):
                isExists=os.path.exists(path)
                if not isExists:
                                os.makedirs(path)
                                return True
                else:
                                return False

def getid():
        exh = open('workdir\\exheader.bin','rb')
        exh.seek(512)
        lid = str(hex(struct.unpack('I',exh.read(4))[0]))[2:]
        hid = str(hex(struct.unpack('I',exh.read(4))[0]))[2:]
        lid = '0'*(8-len(lid))+lid
        hid = '0'*(8-len(hid))+hid
        jumpid = hid+lid
        return jumpid

with open(sys.argv[1], 'rb') as f:
	code = f.read();


save('mountRom', findFunction(code, parseHexStr('0C 00 9D E5 00 10 90 E5  28 10 91 E5 31 FF 2F E1  ')));
save('mountRom', findFunction(code, '\x31\xFF\x2F\xE1\x04\x00\xA0\xE1\x0F\x10\xA0\xE1\xA4\x2F\xB0\xE1'));
save('mountArchive', findFunction(code, '\x10\x00\x97\xE5\xD8\x20\xCD\xE1\x00\x00\x8D'));
save('regArchive', findFunction(code, '\xB4\x44\x20\xC8\x59\x46\x60\xD8'));
save('mountArchive', findFunction(code, '\x28\xD0\x4D\xE2\x00\x40\xA0\xE1\xA8\x60\x9F\xE5\x01\xC0\xA0\xE3'));
save('getServiceHandle', findFunction(code, parseHexStr(' F8 67 A0 D8')));
save('userFsTryOpen', findFunction(code, parseHexStr('0D 10 A0 E1 00 C0 90 E5  04 00 A0 E1 3C FF 2F E1')));
save('userFsTryOpen', findFunction(code, parseHexStr('10 10 8D E2 00 C0 90 E5  05 00 A0 E1 3C FF 2F E1')));


locateHid();
locateFS();
print(repr(addrdb));

for i in addrdb:
	if (addrdb[i] == '0'):
		print('***WARNING*** Failed locating symbol %s , some patches may not work.' % i); 

filePath = 'layeredfs/'+raw_input('Enter the folder of the layeredFS file:');
if len(filePath)==10:
        filePath = filePath+getid()
		
str = 'u32 fsMountArchive = ' + addrdb['mountArchive'] + ';\n';
str += 'u32 fsRegArchive = ' + addrdb['regArchive'] + ';\n';
str += 'u32 userFsTryOpenFile = ' + addrdb['userFsTryOpen'] + ';\n';
str += '#define LAYEREDFS_PREFIX "ram:/' + filePath + '/"\n'

print(str);

with open('plugin\\source\\autogen.h', 'w') as f:
	f.write(str);

if not os.path.exists('workdir\\romfs1'):
        os.system("3dstool -xtf romfs workdir\\romfs1.bin --romfs-dir workdir\\romfs1")
if not os.path.exists('workdir\\romfs2'):
        os.system("3dstool -xtf romfs workdir\\romfs2.bin --romfs-dir workdir\\romfs2")
if not (os.path.exists('workdir\\romfs1')or os.path.exists('workdir\\romfs2')):
        exit

dir1 = 'workdir\\romfs1'
dir2 = 'workdir\\romfs2'
dirout = 'workdir\\'+filePath.replace('/','\\')
mkdir(dirout)
filelist1 = walk(dir1)
filelist2 = walk(dir2)
for filename in filelist2:
        if filename.replace(dir2,dir1) in filelist1:
                compareresult = filecmp.cmp(filename.replace(dir2,dir1),filename)
                if not compareresult:
                        outfilename = filename.replace(dir2,dirout)
                        mkdir(os.path.split(outfilename)[0])
                        shutil.copy(filename,outfilename)
                        print 'Copy: '+outfilename
        elif not filename.replace(dir2,dir1) in filelist1:
                outfilename = filename.replace(dir2,dirout)
                mkdir(os.path.split(outfilename)[0])
                shutil.copy(filename,outfilename)
                print 'Copy: '+outfilename











