

#include "os_util.h"
#include "util.h"

#if defined(WINDOWS)

#include <windows.h>

DWORD getProcessAffinity(HANDLE hProcess) {
	DWORD processMask, systemMask;

	if(!GetProcessAffinityMask(hProcess, &processMask, &systemMask)) {
		return -1;
	} else {
		return processMask;
	}
}

void throwWindowsError (JNIEnv * env, char * format) {
	DWORD err = GetLastError();
	char msg[2000];
	FormatMessage(FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,
				NULL, errno, MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),
				(LPTSTR) msg, sizeof(msg) / sizeof(msg[0]), NULL);
	throwFormattedException(env, "org/xper/exception/ThreadException", format, err, msg);
}

JNIEXPORT void JNICALL Java_org_xper_util_OsUtil_setAffinity
  (JNIEnv * env, jclass obj, jlong mask)
{
	HANDLE hProcess = GetCurrentProcess();
	DWORD affinity = getProcessAffinity(hProcess);
	if (affinity < 0) {
		throwWindowsError(env, "Get CPU affinity fail %d: %s");
	}
	DWORD newAffinity = affinity | mask;
	if (newAffinity != affinity) {
		if (!SetProcessAffinityMask(hProcess, newAffinity)){
			throwWindowsError(env, "Set CPU affinity fail %d: %s");
		}
	}
	DWORD threadAffinity = mask;
	HANDLE hThread = GetCurrentThread();
	if(!SetThreadAffinityMask(hThread, threadAffinity)){
		throwWindowsError(env, "Set CPU affinity fail %d: %s");
	}
}

JNIEXPORT jlong JNICALL Java_org_xper_util_OsUtil_getAffinity
  (JNIEnv * env, jclass obj) {
	HANDLE hProcess = GetCurrentProcess();
	DWORD affinity = getProcessAffinity(hProcess);
	if (affinity < 0) {
		throwWindowsError(env, "Get CPU affinity fail %d: %s");
	}
  	return affinity;
}

typedef long long unsigned julong;
typedef unsigned int    juint;

inline void set_low (jlong* value, jint low )    { *value &= (jlong)0xffffffff << 32;
                                                   *value |= (jlong)(julong)(juint)low; }

inline void set_high(jlong* value, jint high)    { *value &= (jlong)(julong)(juint)0xffffffff;
                                                   *value |= (jlong)high       << 32; }

inline jlong jlong_from(jint h, jint l) {
  jlong result = 0; // initialization to avoid warning
  set_high(&result, h);
  set_low(&result,  l);
  return result;
}

jlong windows_to_java_time(FILETIME wt) {
  jlong a = jlong_from(wt.dwHighDateTime, wt.dwLowDateTime);
  return (a - 116444736000000000LL) / 10;
}

JNIEXPORT jlong JNICALL Java_org_xper_util_OsUtil_getTimeOfDay
  (JNIEnv * env, jclass obj) {
	FILETIME wt;
	GetSystemTimeAsFileTime(&wt);
	return windows_to_java_time(wt);
}

#elif defined(LINUX)

#ifndef __USE_GNU
#define __USE_GNU
#endif

#include <sched.h>
#include <stdlib.h>
#include <errno.h>
#include <string.h>
#include <sys/time.h>

JNIEXPORT void JNICALL Java_org_xper_util_OsUtil_setAffinity
  (JNIEnv * env, jclass obj, jlong mask) {
	cpu_set_t cpu_mask;
#ifdef CPU_ZERO
	CPU_ZERO(&cpu_mask);
#else
	__CPU_ZERO(&cpu_mask);
#endif
	cpu_mask.__bits[0] = mask;
	int ret = sched_setaffinity(0, sizeof(cpu_mask), &cpu_mask);
	if (ret != 0) {
		throwFormattedException(env, "org/xper/exception/ThreadException", "Set CPU affinity fail %d: %s", errno, strerror(errno));
	}
}

JNIEXPORT jlong JNICALL Java_org_xper_util_OsUtil_getAffinity
  (JNIEnv * env, jclass obj) {
   cpu_set_t cpu_mask;
   int ret = sched_getaffinity(0, sizeof(cpu_mask), &cpu_mask);
   if (ret != 0) {
	   throwFormattedException(env, "org/xper/exception/ThreadException", "Get CPU affinity fail %d: %s", errno, strerror(errno));
	}
   unsigned long mask = cpu_mask.__bits[0];
   return mask;
}

JNIEXPORT jlong JNICALL Java_org_xper_util_OsUtil_getTimeOfDay
  (JNIEnv * env, jclass obj) {
	struct timeval time;
	gettimeofday(&time, NULL);
	return ((jlong)time.tv_sec) * 1000000  +  ((jlong)time.tv_usec);
}

#elif defined(MACOS)

#include <sys/time.h>

JNIEXPORT void JNICALL Java_org_xper_util_OsUtil_setAffinity
  (JNIEnv * env, jclass obj, jlong mask) {
}

JNIEXPORT jlong JNICALL Java_org_xper_util_OsUtil_getAffinity
  (JNIEnv * env, jclass obj) {
   return 0;
}

JNIEXPORT jlong JNICALL Java_org_xper_util_OsUtil_getTimeOfDay
  (JNIEnv * env, jclass obj) {
	struct timeval time;
	gettimeofday(&time, NULL);
	return ((jlong)time.tv_sec) * 1000000  +  ((jlong)time.tv_usec);
}

#else

#endif
