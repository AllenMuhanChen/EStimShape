#include "comedi_common.h"

#include "comedi_analog_sw_out_device.h"

#include "util.h"

#include <string.h>
#include <stdlib.h>
#include <errno.h>
#include <unistd.h>

JNIEXPORT jobject JNICALL Java_org_xper_acq_comedi_ComediAnalogSWOutDevice_nCreateTask
  (JNIEnv * env, jobject obj, jstring devString, jint nChannels)
{
	return createComediInsnTask(env, devString, nChannels, COMEDI_SUBD_AO);
}

JNIEXPORT void JNICALL Java_org_xper_acq_comedi_ComediAnalogSWOutDevice_nDestroy
  (JNIEnv * env, jobject obj, jobject handle)
{
	struct ComediHandle * h = (struct ComediHandle *)(*env)->GetDirectBufferAddress(env, handle);
	closeComediDevice(h);
}

JNIEXPORT void JNICALL Java_org_xper_acq_comedi_ComediAnalogSWOutDevice_nCreateChannels
  (JNIEnv * env, jobject obj, jobject handle, jint i, jshort chan, jdouble min, jdouble max, jstring aref)
{
	struct ComediHandle * h = (struct ComediHandle *)(*env)->GetDirectBufferAddress(env, handle);
	
	configComediChannel (h, env, i, chan, min, max, aref);
	
	h->insn[i].insn=INSN_WRITE;
    h->insn[i].n = 1;
    h->insn[i].data=&(h->sample[i]);
    h->insn[i].subdev = h->subdev;
}

JNIEXPORT void JNICALL Java_org_xper_acq_comedi_ComediAnalogSWOutDevice_nWrite
  (JNIEnv * env, jobject obj, jobject handle, jobject buf)
{
	struct ComediHandle * h = (struct ComediHandle *)(*env)->GetDirectBufferAddress(env, handle);
	double * data = (double *)(*env)->GetDirectBufferAddress(env, buf);
	
	int i;
	for (i = 0; i < h->nChannels; i ++) {
		h->sample[i] = comedi_from_phys (data[i], &((h->rangeInfo)[i]), h->maxSample[i]);
	}
		
	int ret=comedi_do_insnlist(h->dev,&(h->insnList));
	if(ret != h->nChannels){
		throwFormattedException (env, "org/xper/exception/ComediException", 
		    						"Error reading comedi data: %s", getComediError());
	}
}


