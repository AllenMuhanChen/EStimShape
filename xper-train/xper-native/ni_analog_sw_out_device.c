
#include "util.h"

#include "ni_analog_sw_out_device.h"

#include "ni_common.h"

JNIEXPORT jobject JNICALL Java_org_xper_acq_ni_NiAnalogSWOutDevice_nCreateTask
  (JNIEnv * env, jobject obj, jint nChannels)
{
	return createNiTask(env, nChannels);
}

JNIEXPORT void JNICALL Java_org_xper_acq_ni_NiAnalogSWOutDevice_nDestroy
  (JNIEnv * env, jobject obj, jobject handle)
{
	destroyNiTask(env, handle);
}

JNIEXPORT void JNICALL Java_org_xper_acq_ni_NiAnalogSWOutDevice_nCreateChannels
  (JNIEnv * env, jobject obj, jobject handle, jstring chan, jdouble min, jdouble max)
{
	struct NiHandle * h = (struct NiHandle *)(*env)->GetDirectBufferAddress(env, handle);
	char * channel = GetStringNativeChars(env, chan);
	DAQmxErrChk (env, DAQmxCreateAOVoltageChan(h->taskHandle,channel,"",min,max,DAQmx_Val_Volts,NULL));
}

JNIEXPORT void JNICALL Java_org_xper_acq_ni_NiAnalogSWOutDevice_nWrite
  (JNIEnv * env, jobject obj, jobject handle, jobject buf)
{
	struct NiHandle * h = (struct NiHandle *)(*env)->GetDirectBufferAddress(env, handle);
	float64 * data = (float64 *)(*env)->GetDirectBufferAddress(env, buf);
	int32 written = 0;
	DAQmxErrChk (env, DAQmxWriteAnalogF64 (h->taskHandle,1,1,10.0,DAQmx_Val_GroupByScanNumber,data, &written, NULL));
	if (written != 1) {
		throwFormattedException(env, "org/xper/exception/NiException", "%i samples expected, %i samples written.", h->nChannels, written*h->nChannels);
	}
}

