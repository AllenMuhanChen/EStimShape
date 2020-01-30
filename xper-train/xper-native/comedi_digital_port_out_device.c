#include "util.h"

#include "comedi_common.h"

#include "comedi_digital_port_out_device.h"

JNIEXPORT jobject JNICALL Java_org_xper_acq_comedi_ComediDigitalPortOutDevice_nCreateTask
  (JNIEnv * env, jobject obj, jstring devString, jobject portBuf, jint linesPerPort)
{
	comedi_set_global_oor_behavior (COMEDI_OOR_NUMBER);

	jobject handle = (jobject)newJavaManagedByteBuffer(env, sizeof(struct ComediHandle));
	struct ComediHandle * h = (struct ComediHandle *)(*env)->GetDirectBufferAddress(env, handle);
	jint * ports = (jint *)(*env)->GetDirectBufferAddress(env, portBuf);
	int nPorts = (*env)->GetDirectBufferCapacity(env, portBuf)/sizeof(jint);

	h->deviceName = GetStringNativeChars(env, devString);
	h->dev = comedi_open(h->deviceName);
	if (h->dev == NULL) {
		throwFormattedException(env, "org/xper/exception/ComediException",
				"Error opening comedi device %s: %s", h-> deviceName, getComediError());
	}
	h->subdev = comedi_find_subdevice_by_type(h->dev,COMEDI_SUBD_DIO,0);
	if (h->subdev == -1) {
		throwFormattedException (env, "org/xper/exception/ComediException",
				"Error finding digital output subdevice for %s: %s", h->deviceName, getComediError());
	}

	int nChannels = comedi_get_n_channels(h->dev, h->subdev);
	if (nChannels < 0) {
		throwFormattedException (env, "org/xper/exception/ComediException",
				"Error getting the number of channels for device %s, subdevice %i: %s", h->deviceName, h->subdev, getComediError());
	}

	h->nPorts = nPorts;

	int i, j;
	for (i = 0; i < nPorts; i ++) {
		int port = ports[i];
		h->ports[i] = port;
		for (j = 0; j < linesPerPort; j ++) {
			unsigned int channelIndex = port * linesPerPort + j;
			if (channelIndex > nChannels - 1) {
				throwFormattedException (env, "org/xper/exception/ComediException",
						"Not enough channels available: max number of channel is %i, "
						"requested channel is %i (port %i)", nChannels, channelIndex, port);
			}
#ifdef DEBUG
		printf ("comedi_dio_config: channel %i #port %i #line %i\n",
				channelIndex, nPorts, linesPerPort);
#endif
			int ret = comedi_dio_config(h->dev,h->subdev,channelIndex,COMEDI_OUTPUT);
			if (ret < 0) {
				throwFormattedException (env, "org/xper/exception/ComediException",
								"Error configuring digital channels %i for output: %s", channelIndex, getComediError());
			}
		}
	}

	unsigned int portMask = 0;
	for (i = 0; i < linesPerPort; i ++) {
		portMask |= 1 << i;
	}
	h->portMask = portMask;
	h->linesPerPort = linesPerPort;

	return handle;
}

JNIEXPORT void JNICALL Java_org_xper_acq_comedi_ComediDigitalPortOutDevice_nDestroy
  (JNIEnv * env, jobject obj, jobject handle)
{
	struct ComediHandle * h = (struct ComediHandle *)(*env)->GetDirectBufferAddress(env, handle);
	closeComediDevice(h);
}

JNIEXPORT void JNICALL Java_org_xper_acq_comedi_ComediDigitalPortOutDevice_nWrite
  (JNIEnv * env, jobject obj, jobject handle, jobject dataBuf)
{
	struct ComediHandle * h = (struct ComediHandle *)(*env)->GetDirectBufferAddress(env, handle);
	jlong * data = (jlong *)(*env)->GetDirectBufferAddress(env, dataBuf);

	int i;
	for (i = 0; i < h->nPorts; i ++) {
		int port = h->ports[i];
		unsigned int bits = data[i];
		unsigned int base = port * h->linesPerPort;
#ifdef DEBUG
		printf ("comedi_dio_bitfield2: Mask %x bits %i base %i #port %i #line %i\n",
				h->portMask, bits, base, h->nPorts, h->linesPerPort);
#endif
		int ret = comedi_dio_bitfield2(h->dev, h->subdev, h->portMask, &bits, base);
		if(ret < 0){
			throwFormattedException (env, "org/xper/exception/ComediException",
										"Error writing comedi digital channels: %s", getComediError());
		}
	}
}

