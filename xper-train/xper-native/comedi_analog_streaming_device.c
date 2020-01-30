
#include "comedi_common.h"

#include "comedi_analog_streaming_device.h"

#include "util.h"

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <errno.h>
#include <unistd.h>

char *cmdtest_messages[]= {
	  "success",
	  "invalid source",
	  "source conflict",
	  "invalid argument",
	  "argument conflict",
	  "invalid chanlist",
};

char * cmd_src(int src,char *buf) {
      buf[0]=0;

      if(src&TRIG_NONE)strcat(buf,"none|");
      if(src&TRIG_NOW)strcat(buf,"now|");
      if(src&TRIG_FOLLOW)strcat(buf, "follow|");
      if(src&TRIG_TIME)strcat(buf, "time|");
      if(src&TRIG_TIMER)strcat(buf, "timer|");
      if(src&TRIG_COUNT)strcat(buf, "count|");
      if(src&TRIG_EXT)strcat(buf, "ext|");
      if(src&TRIG_INT)strcat(buf, "int|");
#ifdef TRIG_OTHER
      if(src&TRIG_OTHER)strcat(buf, "other|");
#endif

      if(strlen(buf)==0){
    	  sprintf(buf,"unknown(0x%08x)",src);
      }else{
          buf[strlen(buf)-1]=0;
      }

      return buf;
}

void dump_cmd(FILE *out,comedi_cmd *cmd)
{
      char buf[100];

      fprintf(out,"start:      %-8s %d\n",
                             cmd_src(cmd->start_src,buf),
                             cmd->start_arg);

      fprintf(out,"scan_begin: %-8s %d\n",
                             cmd_src(cmd->scan_begin_src,buf),
                             cmd->scan_begin_arg);

      fprintf(out,"convert:    %-8s %d\n",
                             cmd_src(cmd->convert_src,buf),
                             cmd->convert_arg);

      fprintf(out,"scan_end:   %-8s %d\n",
                             cmd_src(cmd->scan_end_src,buf),
                             cmd->scan_end_arg);

      fprintf(out,"stop:       %-8s %d\n",
                             cmd_src(cmd->stop_src,buf),
                             cmd->stop_arg);
}

JNIEXPORT void JNICALL Java_org_xper_acq_comedi_ComediAnalogStreamingDevice_nStart
  (JNIEnv * env, jobject obj, jobject handle)
{
	struct ComediHandle * h = (struct ComediHandle *)(*env)->GetDirectBufferAddress(env, handle);
	
	h->channelIndex = 0;
	
	h->dev = comedi_open(h->deviceName);
	if (h->dev == NULL) {
		throwFormattedException(env, "org/xper/exception/ComediException", 
				"Error opening comedi device %s: %s", h->deviceName, getComediError());
	}
	int ret = comedi_command (h->dev, &(h->cmd));
	if (ret == -1) {
        throwFormattedException (env, "org/xper/exception/ComediException", 
        					"Error starting command: %s", getComediError());
    }
}

JNIEXPORT void JNICALL Java_org_xper_acq_comedi_ComediAnalogStreamingDevice_nStop
  (JNIEnv * env, jobject obj, jobject handle)
{
	struct ComediHandle * h = (struct ComediHandle *)(*env)->GetDirectBufferAddress(env, handle);
	
    int ret = comedi_cancel (h->dev, h->subdev);
    if (ret == -1) {
        throwFormattedException (env, "org/xper/exception/ComediException", 
        					"Error stopping command: %s", getComediError());
    }
    closeComediDevice(h);
}

JNIEXPORT jobject JNICALL Java_org_xper_acq_comedi_ComediAnalogStreamingDevice_nCreateTask
  (JNIEnv * env, jobject obj, jstring devString, jint nChannels, jdouble freq, jint bufSize)
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
	
	h->subdev = comedi_find_subdevice_by_type(h->dev,COMEDI_SUBD_AI,0);
	if (h->subdev == -1) {
		throwFormattedException (env, "org/xper/exception/ComediException", 
				"Error finding analog input subdevice for %s: %s", h->deviceName, getComediError());
	}
	
	h->subdevFlags = comedi_get_subdevice_flags(h->dev, h->subdev);
	if(h->subdevFlags & SDF_LSAMPL) {
		h->bytesPerSample = sizeof(lsampl_t);
	} else {
		h->bytesPerSample = sizeof(sampl_t);
	}
			 
	h->nChannels = nChannels;
	
	h->bufferSize = bufSize * h->bytesPerSample;
	h->sampleBuffer = malloc(h->bufferSize);
	
	memset (&(h->cmd), 0, sizeof(h->cmd));
	
	(h->cmd).chanlist = h->chanlist;
	(h->cmd).chanlist_len = h->nChannels;
	
	(h->cmd).subdev = h->subdev;
	(h->cmd).flags = 0;
	(h->cmd).start_src = TRIG_NOW;
	(h->cmd).start_arg = 0;
	(h->cmd).scan_begin_src = TRIG_TIMER;
	(h->cmd).scan_begin_arg = (unsigned int) (1e9 / freq);
	(h->cmd).convert_src = TRIG_TIMER;
	(h->cmd).convert_arg = (unsigned int) (1e9 / freq / h->nChannels);
	(h->cmd).scan_end_src = TRIG_COUNT;
	(h->cmd).scan_end_arg = nChannels;
	(h->cmd).stop_src = TRIG_NONE;
	(h->cmd).stop_arg = 0;

	return handle;
}

JNIEXPORT void JNICALL Java_org_xper_acq_comedi_ComediAnalogStreamingDevice_nDestroy
  (JNIEnv * env, jobject obj, jobject handle)
{
	struct ComediHandle * h = (struct ComediHandle *)(*env)->GetDirectBufferAddress(env, handle);
	
	if (h->sampleBuffer) {
		free (h->sampleBuffer);
		h->sampleBuffer = NULL;
	}
	closeComediDevice(h);
}

JNIEXPORT void JNICALL Java_org_xper_acq_comedi_ComediAnalogStreamingDevice_nCreateChannels
  (JNIEnv * env, jobject obj, jobject handle, jint i, jshort chan, jdouble min, jdouble max, jstring aref)
{
	struct ComediHandle * h = (struct ComediHandle *)(*env)->GetDirectBufferAddress(env, handle);
	
	configComediChannel(h, env, i, chan, min, max, aref);
}

JNIEXPORT void JNICALL Java_org_xper_acq_comedi_ComediAnalogStreamingDevice_nConfigTask
  (JNIEnv * env, jobject obj, jobject handle)
{
	struct ComediHandle * h = (struct ComediHandle *)(*env)->GetDirectBufferAddress(env, handle);
	
	fprintf(stdout, "Trying command ...\n");
	dump_cmd(stdout, &(h->cmd));
	int ret = comedi_command_test(h->dev,&(h->cmd));
	if(ret < 0){
        if(errno == EIO){
        	throwException(env, "org/xper/exception/ComediException", "Ummm... this subdevice doesn't support commands.");
        }
        throwFormattedException (env, "org/xper/exception/ComediException", 
            					"Comedi command test error: %s", getComediError());
	}
	fprintf(stdout,"First test returned %d (%s)\n", ret, cmdtest_messages[ret]);

	if (ret != 0) {
        fprintf(stdout, "Trying command ...\n");
        dump_cmd(stdout, &(h->cmd));
        ret = comedi_command_test(h->dev,&(h->cmd));

        if(ret<0){
        	throwFormattedException (env, "org/xper/exception/ComediException", 
        	            					"Comedi command test error: %s", getComediError());
        }
        fprintf(stdout,"Second test returned %d (%s)\n", ret,
                                                cmdtest_messages[ret]);
        if(ret!=0){
        	throwException(env, "org/xper/exception/ComediException", "Error preparing command.");
        }
	}
	
	if (h->dev != NULL) {
		comedi_close (h->dev);
		h->dev = NULL;
	}
	
	fflush(stdout);
}

/**
 * Return number of samples read.
 * */
JNIEXPORT jint JNICALL Java_org_xper_acq_comedi_ComediAnalogStreamingDevice_nScan
  (JNIEnv * env, jobject obj, jobject handle, jobject buf)
{
	struct ComediHandle * h = (struct ComediHandle *)(*env)->GetDirectBufferAddress(env, handle);
	
	int ret = comedi_poll (h->dev, h->subdev); 
    if (ret == -1) {
    	throwFormattedException (env, "org/xper/exception/ComediException", 
    					"Error polling device: %s", getComediError());
    }
    
    /* Setting minimal read block size does not make any performance difference. 
     * So just read whatever is available. */
    int bytesToRead = comedi_get_buffer_contents(h->dev, h->subdev);
    if (bytesToRead == -1) {
       	throwFormattedException (env, "org/xper/exception/ComediException", 
        				"Error getting buffer size: %s", getComediError());
    }
    if (bytesToRead > h->bufferSize) {
    	bytesToRead = h->bufferSize;
    }
	
    int fileno = comedi_fileno(h->dev);
    int n = read (fileno, h->sampleBuffer, bytesToRead);
    if (n > 0) {
    	if (n % h->bytesPerSample == 0) {
    		int nSample = n / h->bytesPerSample;
    		double * data = (double *)(*env)->GetDirectBufferAddress(env, buf);
    		int i;
    		for (i = 0; i < nSample; i ++) {
    			lsampl_t raw;
    			if(h->subdevFlags & SDF_LSAMPL) {
    				raw = ((lsampl_t *)h->sampleBuffer)[i];
    			} else {
    				raw = ((sampl_t *)h->sampleBuffer)[i];
    			}

    			data[i] = comedi_to_phys (raw, &((h->rangeInfo)[h->channelIndex]), h->maxSample[h->channelIndex]);
    			
    			h->channelIndex += 1;
    			if (h->channelIndex == h->nChannels) {
    				h->channelIndex = 0;
    			}
    		}
    		return nSample;
        } else {
        	throwFormattedException (env, "org/xper/exception/ComediException", 
        	    						"Data should come in as %i bytes per sample.", h->bytesPerSample);
        }
    } else if (n == 0) {
    	return 0;
    } else {
    	throwFormattedException (env, "org/xper/exception/ComediException", 
    						"Error reading comedi data: %s", getComediError());
    }
    return 0;
}



