
#include "util.h"

#include "ni_analog_sampling_device.h"

#include "ni_common.h"


JNIEXPORT jobject JNICALL Java_org_xper_acq_ni_NiAnalogSamplingDevice_nCreateTask
  (JNIEnv * env, jobject obj, jint nChannels)
{
	return createNiTask(env, nChannels);
}

JNIEXPORT void JNICALL Java_org_xper_acq_ni_NiAnalogSamplingDevice_nDestroy
  (JNIEnv * env, jobject obj, jobject handle)
{
	destroyNiTask(env, handle);
}

JNIEXPORT void JNICALL Java_org_xper_acq_ni_NiAnalogSamplingDevice_nCreateChannels
  (JNIEnv * env, jobject obj, jobject handle, jstring chan, jdouble min, jdouble max)
{
	struct NiHandle * h = (struct NiHandle *)(*env)->GetDirectBufferAddress(env, handle);
	char * channel = GetStringNativeChars(env, chan);
	DAQmxErrChk (env, DAQmxCreateAIVoltageChan(h->taskHandle,channel,"",DAQmx_Val_Cfg_Default,min,max,DAQmx_Val_Volts,NULL));
}

JNIEXPORT void JNICALL Java_org_xper_acq_ni_NiAnalogSamplingDevice_nScan
  (JNIEnv * env, jobject obj, jobject handle, jobject buf)
{
	/*struct NiHandle * h = (struct NiHandle *)(*env)->GetDirectBufferAddress(env, handle);*/
	int samplePerChan = 1;
	int32 read = niAnalogRead(env, handle, buf, samplePerChan);
	if (read != samplePerChan) {
		throwFormattedException(env, "org/xper/exception/NiException", "%i samples expected, %i samples read.", samplePerChan, read);
	}
}
