
#include "ni_common.h"
#include "util.h"

char errBuff[2048]={'\0'};

void handleNiError (JNIEnv * env, int32 error)
{
	DAQmxGetExtendedErrorInfo(errBuff,2048);
	throwException(env, "org/xper/exception/NiException", errBuff);
}

int32 niAnalogRead (JNIEnv * env, jobject handle, jobject buf, int32 numSamples)
{
	struct NiHandle * h = (struct NiHandle *)(*env)->GetDirectBufferAddress(env, handle);
	float64 * data = (float64 *)(*env)->GetDirectBufferAddress(env, buf);
	jlong capacity = (*env)->GetDirectBufferCapacity(env, buf);
	int32 read = 0;
	DAQmxErrChk (env, DAQmxReadAnalogF64(h->taskHandle,numSamples,10.0,DAQmx_Val_GroupByScanNumber,data,capacity/sizeof(float64),&read,NULL));
	return read;
}

jobject createNiTask (JNIEnv * env, int nChannels) 
{
	jobject handle = (jobject)newJavaManagedByteBuffer(env, sizeof(struct NiHandle));
	struct NiHandle * h = (struct NiHandle *)(*env)->GetDirectBufferAddress(env, handle);
	DAQmxErrChk (env, DAQmxCreateTask("",&(h->taskHandle)));
	h->nChannels = nChannels;
	return handle;
}

void destroyNiTask (JNIEnv * env, jobject handle)
{
	struct NiHandle * h = (struct NiHandle *)(*env)->GetDirectBufferAddress(env, handle);
	if (h->taskHandle != 0) {
		DAQmxErrChk (env, DAQmxClearTask(h->taskHandle));
	}
}

void startNiTask (JNIEnv * env, jobject handle)
{
	struct NiHandle * h = (struct NiHandle *)(*env)->GetDirectBufferAddress(env, handle);
	DAQmxErrChk (env, DAQmxStartTask(h->taskHandle)); 
}

void stopNiTask (JNIEnv * env, jobject handle)
{
	struct NiHandle * h = (struct NiHandle *)(*env)->GetDirectBufferAddress(env, handle);
	if (h->taskHandle != 0) {
		DAQmxStopTask(h->taskHandle);
	}
}
