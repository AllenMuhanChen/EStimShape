
# Change the following variables according to system setup.
JAVA_HOME = C:\Program Files\Java\jdk1.8.0_74
# Path of the xper class files
XPER_CLASSPATH = C:\Users\a1_ram\Dropbox\Share_xper\stim\xper_sach7\xper\class

JAVAH = ${JAVA_HOME}\bin\javah

# Do not change below this
DIST = windows
CLASSPATH= -classpath $(XPER_CLASSPATH)

NI_INC_PATH = -I"..\xper\lib\MinGW-NIDAQmx"
NI_LIB_PATH = -L"..\xper\lib\MinGW-NIDAQmx"
NI_LIB = $(NI_LIB_PATH) -lnidaq

XPER_LIB =

INC_PATH = -I"$(JAVA_HOME)\include" -I"$(JAVA_HOME)\include\win32" $(NI_INC_PATH)

CFLAGS = -DWINDOWS -DNI_MX_DRIVER
LFLAGS = -shared

XPER = xper.dll
XPER_DEF = xper.def

XPER_NI = xper-ni.dll
XPER_NI_DEF = xper-ni.def

TARGET = xper ni

include common.mk