set PATH=%PATH%;C:\devkitPro\devkitARM\bin
del plugin\source\autogen.h
ctrtool --decompresscode -t exefs --exefsdir=workdir\exefs workdir\exefs.bin
locate.py workdir\exefs\code.bin
cd plugin
build.py
cd ..
copy plugin\payload.bin workdir\layeredfs.plg
placeplg.py
rd workdir\romfs1 /s/q
rd workdir\romfs2 /s/q
pause