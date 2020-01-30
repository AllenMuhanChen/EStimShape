#ifndef NI_COMMON_H_
#define NI_COMMON_H_

#ifdef NI_BASE_DRIVER
#include <NIDAQmxBase.h>

#define DAQmxGetExtendedErrorInfo DAQmxBaseGetExtendedErrorInfo
#define DAQmxReadAnalogF64 DAQmxBaseReadAnalogF64
#define DAQmxCreateAIVoltageChan DAQmxBaseCreateAIVoltageChan
#define DAQmxCfgInputBuffer DAQmxBaseCfgInputBuffer
#define DAQmxCfgSampClkTiming DAQmxBaseCfgSampClkTiming
#define DAQmxCreateAOVoltageChan DAQmxBaseCreateAOVoltageChan
#define DAQmxWriteAnalogF64 DAQmxBaseWriteAnalogF64
#define DAQmxCreateDOChan DAQmxBaseCreateDOChan
#define DAQmxWriteDigitalU32 DAQmxBaseWriteDigitalU32
#define DAQmxCreateTask DAQmxBaseCreateTask
#define DAQmxClearTask DAQmxBaseClearTask
#define DAQmxStartTask DAQmxBaseStartTask
#define DAQmxStopTask DAQmxBaseStopTask

#endif

#ifdef NI_MX_DRIVER
#include <NIDAQmx.h>
#endif

#include <jni.h>

#ifdef __cplusplus
extern "C" {
#endif

#define DAQmxErrChk(env, functionCall) {int32 error = 0; if( DAQmxFailed(error=(functionCall)) ) handleNiError(env, error); }

struct NiHandle {
	TaskHandle  taskHandle;
	jint nChannels;
};

void handleNiError (JNIEnv * env, int32 error);

jobject createNiTask (JNIEnv * env, int nChannels);
void destroyNiTask (JNIEnv * env, jobject handle);
void startNiTask (JNIEnv * env, jobject handle);
void stopNiTask (JNIEnv * env, jobject handle);
int32 niAnalogRead (JNIEnv * env, jobject handle, jobject buf, int32 numSamples);

#ifdef __cplusplus
}
#endif
#endif /*NI_COMMON_H_*/
