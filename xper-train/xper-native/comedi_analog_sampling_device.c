
#include "comedi_common.h"

#include "comedi_analog_sampling_device.h"

#include "util.h"

#include <string.h>
#include <stdlib.h>
#include <errno.h>
#include <unistd.h>

JNIEXPORT void JNICALL Java_org_xper_acq_comedi_ComediAnalogSamplingDevice_nDestroy
  (JNIEnv * env, jobject obj, jobject handle)
{
	struct ComediHandle * h = (struct ComediHandle *)(*env)->GetDirectBufferAddress(env, handle);
	closeComediDevice(h);
}

JNIEXPORT jobject JNICALL Java_org_xper_acq_comedi_ComediAnalogSamplingDevice_nCreateTask
  (JNIEnv * env, jobject obj, jstring devString, jint nChannels)
{
	return createComediInsnTask(env, devString, nChannels, COMEDI_SUBD_AI);
}

JNIEXPORT void JNICALL Java_org_xper_acq_comedi_ComediAnalogSamplingDevice_nCreateChannels
  (JNIEnv * env, jobject obj, jobject handle, jint i, jshort chan, jdouble min, jdouble max, jstring aref)
{
	struct ComediHandle * h = (struct ComediHandle *)(*env)->GetDirectBufferAddress(env, handle);
	
	configComediChannel(h, env, i, chan, min, max, aref);
    
    h->insn[i].insn=INSN_READ;
    h->insn[i].n = 1;
    h->insn[i].data=&(h->sample[i]);
    h->insn[i].subdev = h->subdev;
    h->insn[i].chanspec = h->chanlist[i];
}

JNIEXPORT void JNICALL Java_org_xper_acq_comedi_ComediAnalogSamplingDevice_nScan
  (JNIEnv * env, jobject obj, jobject handle, jobject buf)
{
	struct ComediHandle * h = (struct ComediHandle *)(*env)->GetDirectBufferAddress(env, handle);
	
	int ret=comedi_do_insnlist(h->dev,&(h->insnList));
	if(ret != h->nChannels){
		throwFormattedException (env, "org/xper/exception/ComediException", 
		    						"Error reading comedi data: %s", getComediError());
	}
	
	double * data = (double *)(*env)->GetDirectBufferAddress(env, buf);
	
	int i;
	for (i = 0; i < ret; i ++) {
		data[i] = comedi_to_phys (h->sample[i], &((h->rangeInfo)[i]), h->maxSample[i]);
	}
}

