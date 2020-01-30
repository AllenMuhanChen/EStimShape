
#include "comedi_common.h"
#include "util.h"

#include <string.h>

char * getComediError ()
{
	char * error = comedi_strerror(comedi_errno());
	return error;
}

void closeComediDevice (struct ComediHandle * h)
{
	if (h->dev != NULL) {
		comedi_close (h->dev);
		h->dev = NULL;
	}
}

jobject createComediInsnTask (JNIEnv * env, jstring devString, jint nChannels, int devType)
{
	comedi_set_global_oor_behavior (COMEDI_OOR_NUMBER);
		
	jobject handle = (jobject)newJavaManagedByteBuffer(env, sizeof(struct ComediHandle));
	struct ComediHandle * h = (struct ComediHandle *)(*env)->GetDirectBufferAddress(env, handle);
	
	h->deviceName = GetStringNativeChars(env, devString);
	h->dev = comedi_open(h->deviceName);
	if (h->dev == NULL) {
		throwFormattedException(env, "org/xper/exception/ComediException", 
				"Error opening comedi device %s: %s", h-> deviceName, getComediError());
	}
	h->subdev = comedi_find_subdevice_by_type(h->dev,devType,0);
	if (h->subdev == -1) {
		throwFormattedException (env, "org/xper/exception/ComediException", 
				"Error finding analog input subdevice for %s: %s", h->deviceName, getComediError());
	}
	h->nChannels = nChannels;
	
	h->insnList.n_insns=nChannels;
	h->insnList.insns=h->insn;
	
	return handle;
}

void configComediChannel (struct ComediHandle * h, JNIEnv * env, jint i, jshort chan, jdouble min, jdouble max, jstring aref)
{
	if (i >= COMEDI_MAX_CHAN) {
		throwFormattedException (env, "org/xper/exception/ComediException", 
		    					"Maximum channels supported is %d, requesting %d", COMEDI_MAX_CHAN, i);
	}
	
	char * refString = GetStringNativeChars(env, aref);
	
	int ref = AREF_DIFF;
    if (strcmp(refString, "ground") == 0) {
    	ref = AREF_GROUND;
    } else if (strcmp(refString, "diff") == 0) {
    	ref = AREF_DIFF;
    } else if (strcmp(refString, "common") == 0) {
    	ref = AREF_COMMON;
    } else if (strcmp(refString, "other") == 0) {
    	ref = AREF_OTHER;
    }
    int range = comedi_find_range (h->dev, h->subdev, chan, UNIT_volt, min, max);
    if (range == -1) {
    	throwFormattedException (env, "org/xper/exception/ComediException", 
    					"Error finding range (device %s, chanel %i): %s", h->deviceName, chan, getComediError());
    }

	h->chanlist[i] = CR_PACK(chan, range, ref);
	
	memcpy (&((h->rangeInfo)[i]), comedi_get_range (h->dev, h->subdev, chan, range), sizeof (comedi_range));
	(h->maxSample)[i] = comedi_get_maxdata (h->dev, h->subdev, chan);
}

