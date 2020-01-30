
#include "util.h"
#include <stdlib.h>

void throwException(JNIEnv * env, const char *exception_name, const char * err) {
	jclass cls;

	if ((*env)->ExceptionCheck(env) == JNI_TRUE)
		return; // The JVM crashes if we try to throw two exceptions from one native call
	cls = (*env)->FindClass(env, exception_name);
	(*env)->ThrowNew(env, cls, err);
}

jobject newJavaManagedByteBuffer(JNIEnv *env, const int size) {
  jclass bufferutils_class = (*env)->FindClass(env, "org/lwjgl/BufferUtils");
  jmethodID createByteBuffer = (*env)->GetStaticMethodID(env, bufferutils_class, "createByteBuffer", "(I)Ljava/nio/ByteBuffer;");
  jobject buffer = (*env)->CallStaticObjectMethod(env, bufferutils_class, createByteBuffer, size);
  return buffer;
}

static jstring sprintfJavaString(JNIEnv *env, const char *format, va_list ap) {
#define BUFFER_SIZE 4000
	char buffer[BUFFER_SIZE];
	jstring str;
#ifdef _MSC_VER
	vsnprintf_s(buffer, BUFFER_SIZE, _TRUNCATE, format, ap);
#else
	vsnprintf(buffer, BUFFER_SIZE, format, ap);
#endif
	buffer[BUFFER_SIZE - 1] = '\0';
	str = (*env)->NewStringUTF(env, buffer);
	return str;
}

void throwFormattedException(JNIEnv * env, const char *exception_name, const char *format, ...) {
	jclass cls;
	jstring str;
	jmethodID exception_constructor;
	jobject exception;

	if ((*env)->ExceptionCheck(env) == JNI_TRUE)
		return; // The JVM crashes if we try to throw two exceptions from one native call
	
	va_list ap;
	va_start(ap, format);
	
	str = sprintfJavaString(env, format, ap);
	cls = (*env)->FindClass(env, exception_name);
    exception_constructor = (*env)->GetMethodID(env, cls, "<init>", "(Ljava/lang/String;)V");
	exception = (*env)->NewObject(env, cls, exception_constructor, str);
	(*env)->Throw(env, exception);
	
	va_end(ap);
}

// retrieves the locale-specific C string
char * GetStringNativeChars(JNIEnv *env, jstring jstr) { 
  jbyteArray bytes = 0; 
  jthrowable exc; 
  char *result = 0; 
  jclass jcls_str;
  jmethodID MID_String_getBytes;

  /* out of memory error? */ 
  if ((*env)->EnsureLocalCapacity(env, 2) < 0) { 
    return 0; 
  } 

  // aquire getBytes method
  jcls_str = (*env)->FindClass(env, "java/lang/String"); 
  MID_String_getBytes = (*env)->GetMethodID(env, jcls_str, "getBytes", "()[B"); 

  // get the bytes
  bytes = (jbyteArray) (*env)->CallObjectMethod(env, jstr, MID_String_getBytes); 
  exc = (*env)->ExceptionOccurred(env); 

  // if no exception occured while getting bytes - continue
  if (!exc) { 
    jint len = (*env)->GetArrayLength(env, bytes); 
    result = (char *) malloc(len + 1); 
    if (result == 0) { 
      throwException(env, "java/lang/OutOfMemoryError", NULL); 
      (*env)->DeleteLocalRef(env, bytes); 
      return 0; 
    } 
    (*env)->GetByteArrayRegion(env, bytes, 0, len, (jbyte *) result); 
    result[len] = 0; /* NULL-terminate */ 
  } else { 
    (*env)->DeleteLocalRef(env, exc); 
  } 
  (*env)->DeleteLocalRef(env, bytes); 
  return (char*) result;
}


