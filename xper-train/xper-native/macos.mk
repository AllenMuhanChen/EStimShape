
# Change the following variables according to system setup.
JAVA_HOME = /System/Library/Frameworks/JavaVM.framework
# Path of the xper class files
XPER_CLASSPATH = /Users/ecpc32/Dropbox/Share/xper_sach7/xper-sach/class
NI_DRIVER_PATH = /Applications/National\ Instruments/NI-DAQmx\ Base

# Do not change below this
JAVAH = ${JAVA_HOME}/Commands/javah

DIST = macos
CLASSPATH= -classpath $(XPER_CLASSPATH)

NI_INC_PATH = -I$(NI_DRIVER_PATH)/includes
NI_LIB_PATH =
NI_LIB = $(NI_LIB_PATH) -framework nidaqmxbase -framework nidaqmxbaselv -framework JavaVM

XPER_LIB_PATH =
XPER_LIB = $(XPER_LIB_PATH) -framework JavaVM

INC_PATH = -I"$(JAVA_HOME)/Headers" $(NI_INC_PATH)

CFLAGS = -DMACOS -DNI_BASE_DRIVER -arch i386
LFLAGS = -dynamiclib -arch i386

XPER = libxper.jnilib
XPER_DEF =

XPER_NI = libxper-ni.jnilib
XPER_NI_DEF =

TARGET = xper ni

include common.mk
