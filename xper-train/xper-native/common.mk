

all : $(TARGET)

xper : $(XPER)

ni : $(XPER_NI)

comedi : $(XPER_COMEDI)

bindcpu : bindcpu.o
	gcc -o bindcpu $^ 
	mkdir -p ../dist/native/$(DIST)
	mkdir -p $(DIST)
	mv bindcpu $(DIST)
	cp $(DIST)/bindcpu ../dist/native/$(DIST) 

$(XPER) : $(XPER_DEF) \
	util.o os_util.o
	gcc $(LFLAGS) -o $(XPER) $^ $(XPER_LIB)
	mkdir -p ../dist/native/$(DIST)
	mkdir -p $(DIST)
	mv $(XPER) $(DIST)
	cp $(DIST)/$(XPER) ../dist/native/$(DIST)
	
$(XPER_COMEDI) : $(XPER_COMEDI_DEF) \
	util.o comedi_analog_streaming_device.o comedi_common.o comedi_analog_sampling_device.o comedi_analog_sw_out_device.o \
	comedi_digital_port_out_device.o
	gcc $(LFLAGS) -o $(XPER_COMEDI) $^ $(COMEDI_LIB)
	mkdir -p ../dist/native/$(DIST)
	mkdir -p $(DIST)
	mv $(XPER_COMEDI) $(DIST)
	cp $(DIST)/$(XPER_COMEDI) ../dist/native/$(DIST)
	
comedi_digital_port_out_device.o : comedi_digital_port_out_device.h comedi_digital_port_out_device.c

comedi_digital_port_out_device.h : ../xper/src/org/xper/acq/comedi/ComediDigitalPortOutDevice.java
	${JAVAH} $(CLASSPATH) -o comedi_digital_port_out_device.h org.xper.acq.comedi.ComediDigitalPortOutDevice
	
comedi_analog_sw_out_device.o : comedi_analog_sw_out_device.h comedi_analog_sw_out_device.c

comedi_analog_sw_out_device.h : ../xper/src/org/xper/acq/comedi/ComediAnalogSWOutDevice.java
	${JAVAH} $(CLASSPATH) -o comedi_analog_sw_out_device.h org.xper.acq.comedi.ComediAnalogSWOutDevice
		
comedi_analog_sampling_device.o : comedi_analog_sampling_device.h comedi_analog_sampling_device.c

comedi_analog_sampling_device.h : ../xper/src/org/xper/acq/comedi/ComediAnalogSamplingDevice.java
	${JAVAH} $(CLASSPATH) -o comedi_analog_sampling_device.h org.xper.acq.comedi.ComediAnalogSamplingDevice
	
comedi_analog_streaming_device.o : comedi_analog_streaming_device.h comedi_analog_streaming_device.c

comedi_common.o : comedi_common.h comedi_common.c

comedi_analog_streaming_device.h : ../xper/src/org/xper/acq/comedi/ComediAnalogStreamingDevice.java
	${JAVAH} $(CLASSPATH) -o comedi_analog_streaming_device.h org.xper.acq.comedi.ComediAnalogStreamingDevice


util.o : util.h util.c

os_util.o : os_util.h os_util.c

os_util.h : ../xper/src/org/xper/util/OsUtil.java
	${JAVAH} $(CLASSPATH) -o os_util.h org.xper.util.OsUtil

.c.o:
	gcc $(INC_PATH) -Wall $(CFLAGS) -g -c $*.c
	
clean:
	rm -f os_util.h \
		comedi_analog_streaming_device.h comedi_digital_port_out_device.h \
		comedi_analog_sampling_device.h comedi_analog_sw_out_device.h \
		*.o $(XPER) $(XPER_NI) $(XPER_COMEDI) \
		bindcpu.o bindcpu
