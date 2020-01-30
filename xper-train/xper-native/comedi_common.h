#ifndef COMEDI_COMMON_H_
#define COMEDI_COMMON_H_

#include <comedilib.h>
#include <jni.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COMEDI_MAX_CHAN 256

struct ComediHandle {
	char * deviceName;
	comedi_t * dev;
	unsigned int subdev;
	jint nChannels;

	int subdevFlags;
	int bytesPerSample;

	comedi_range rangeInfo [COMEDI_MAX_CHAN];
	lsampl_t maxSample [COMEDI_MAX_CHAN];
	unsigned int chanlist[COMEDI_MAX_CHAN];

	/* Streaming acquisition */
	comedi_cmd cmd;

	/* Buffer to save sample data. */
	sampl_t * sampleBuffer;
	/* Buffer size in bytes. */
	jint bufferSize;
	/* Index of the current channel into the channel arrays. */
	int channelIndex;

	/* Multiple acquisition */
	comedi_insnlist insnList;
	comedi_insn insn [COMEDI_MAX_CHAN];
	lsampl_t sample [COMEDI_MAX_CHAN];

	/* Write mask for digital IO. */
	int ports [COMEDI_MAX_CHAN];
	int nPorts;
	unsigned int portMask;
	int linesPerPort;
};

char * getComediError ();

void closeComediDevice (struct ComediHandle * h);

jobject createComediInsnTask (JNIEnv * env, jstring devString, jint nChannels, int devType);

void configComediChannel (struct ComediHandle * h, JNIEnv * env, jint i, jshort chan, jdouble min, jdouble max, jstring aref);

#ifdef __cplusplus
}
#endif
#endif /*COMEDI_COMMON_H_*/
