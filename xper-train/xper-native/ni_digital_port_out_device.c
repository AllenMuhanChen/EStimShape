
#include "util.h"

#include "ni_common.h"

#include "ni_digital_port_out_device.h"

#define MAX_CHANNELS 256

JNIEXPORT jobject JNICALL Java_org_xper_acq_ni_NiDigitalPortOutDevice_nCreateTask
  (JNIEnv * env, jobject obj, jint nPorts)
{
	if (nPorts > MAX_CHANNELS) {
		throwFormattedException(env, "org/xper/exception/NiException", "%i channels requested. Maximum is %i.", nPorts, MAX_CHANNELS);
	}
	return createNiTask(env, nPorts);
}

JNIEXPORT void JNICALL Java_org_xper_acq_ni_NiDigitalPortOutDevice_nDestroy
  (JNIEnv * env, jobject obj, jobject handle)
{
	destroyNiTask(env, handle);
}

JNIEXPORT void JNICALL Java_org_xper_acq_ni_NiDigitalPortOutDevice_nCreateChannels
  (JNIEnv * env, jobject obj, jobject handle, jstring port)
{
	struct NiHandle * h = (struct NiHandle *)(*env)->GetDirectBufferAddress(env, handle);
	char * channel = GetStringNativeChars(env, port);
	DAQmxErrChk (env, DAQmxCreateDOChan(h->taskHandle,channel,"",DAQmx_Val_ChanForAllLines));
}

JNIEXPORT void JNICALL Java_org_xper_acq_ni_NiDigitalPortOutDevice_nWrite
  (JNIEnv * env, jobject obj, jobject handle, jobject buf)
{
	struct NiHandle * h = (struct NiHandle *)(*env)->GetDirectBufferAddress(env, handle);
	jlong * data = (jlong *)(*env)->GetDirectBufferAddress(env, buf);
	uInt32 cData [MAX_CHANNELS];
	int i = 0;
	for (i = 0; i < h->nChannels; i ++) {
		cData[i] = data[i];
	}
	int32 written = 0;
	DAQmxErrChk (env, DAQmxWriteDigitalU32(h->taskHandle,1,1,10.0,DAQmx_Val_GroupByScanNumber,cData,&written,NULL));
	if (written != 1) {
		throwFormattedException(env, "org/xper/exception/NiException", "%i samples expected, %i samples written.", h->nChannels, written*h->nChannels);
	}
}


