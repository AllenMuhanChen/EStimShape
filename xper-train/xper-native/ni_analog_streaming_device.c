
#include "ni_common.h"

#include "ni_analog_streaming_device.h"

#include "util.h"

JNIEXPORT void JNICALL Java_org_xper_acq_ni_NiAnalogStreamingDevice_nStart
  (JNIEnv * env, jobject obj, jobject handle)
{
	startNiTask(env, handle);
}

JNIEXPORT void JNICALL Java_org_xper_acq_ni_NiAnalogStreamingDevice_nStop
  (JNIEnv * env, jobject obj, jobject handle)
{
	stopNiTask(env, handle);
}

JNIEXPORT jobject JNICALL Java_org_xper_acq_ni_NiAnalogStreamingDevice_nCreateTask
  (JNIEnv * env, jobject obj, jint nChannels)
{
	return createNiTask(env, nChannels);
}

JNIEXPORT void JNICALL Java_org_xper_acq_ni_NiAnalogStreamingDevice_nDestroy
  (JNIEnv * env, jobject obj, jobject handle)
{
	destroyNiTask(env, handle);
}

JNIEXPORT void JNICALL Java_org_xper_acq_ni_NiAnalogStreamingDevice_nCreateChannels
  (JNIEnv * env, jobject obj, jobject handle, jstring chan, jdouble min, jdouble max)
{
	struct NiHandle * h = (struct NiHandle *)(*env)->GetDirectBufferAddress(env, handle);
	char * channel = GetStringNativeChars(env, chan);
	DAQmxErrChk (env, DAQmxCreateAIVoltageChan(h->taskHandle,channel,NULL,DAQmx_Val_Cfg_Default,min,max,DAQmx_Val_Volts,NULL));
}

JNIEXPORT void JNICALL Java_org_xper_acq_ni_NiAnalogStreamingDevice_nConfigTask
  (JNIEnv * env, jobject obj, jobject handle, jdouble rate, jlong bufSize)
{
	struct NiHandle * h = (struct NiHandle *)(*env)->GetDirectBufferAddress(env, handle);
	/* If the bufSize is smaller than default value, it is ignored. */
	DAQmxErrChk (env, DAQmxCfgInputBuffer(h->taskHandle,bufSize));
	DAQmxErrChk (env, DAQmxCfgSampClkTiming(h->taskHandle,NULL,rate,DAQmx_Val_Rising,DAQmx_Val_ContSamps,bufSize));
}

JNIEXPORT jint JNICALL Java_org_xper_acq_ni_NiAnalogStreamingDevice_nScan
  (JNIEnv * env, jobject obj, jobject handle, jobject buf)
{
	/* Read all available samples. Do not wait. */
	return niAnalogRead(env, handle, buf, DAQmx_Val_Auto);
}


