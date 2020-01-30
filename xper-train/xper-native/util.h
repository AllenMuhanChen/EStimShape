
#include <jni.h>

#ifndef UTIL_H_
#define UTIL_H_

#ifdef __cplusplus
extern "C" {
#endif

extern void throwException(JNIEnv * env, const char *exception_name, const char * err);
extern void throwFormattedException(JNIEnv * env, const char *exception_name, const char *format, ...);
extern jobject newJavaManagedByteBuffer(JNIEnv *env, const int size);

extern char * GetStringNativeChars(JNIEnv *env, jstring jstr);

#ifdef __cplusplus
}
#endif


#endif /*UTIL_H_*/

