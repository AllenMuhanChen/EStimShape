package org.xper.config;

import java.util.LinkedList;
import java.util.List;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.ExternalValue;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.springframework.config.java.util.DefaultScopes;
import org.xper.XperConfig;
import org.xper.acq.AcqChannelFactory;
import org.xper.acq.DatabaseDataBuffer;
import org.xper.acq.DefaultAcqDeviceController;
import org.xper.acq.DefaultDataFilterController;
import org.xper.acq.SocketDataAcqClient;
import org.xper.acq.SocketDataAcqServer;
import org.xper.acq.comedi.ComediAnalogStreamingDevice;
import org.xper.acq.device.AcqStreamingDevice;
import org.xper.acq.ni.NiAnalogStreamingDevice;
import org.xper.exception.ExperimentSetupException;
import org.xper.time.SocketTimeClient;
import org.xper.time.SocketTimeServer;


@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(BaseConfig.class)
public class AcqConfig {
	@Autowired BaseConfig baseConfig;
	
	public String DAQ_COMEDI = "comedi";
	public String DAQ_NI = "ni";
	public String DAQ_NONE = "none";
	
	@ExternalValue("acq.driver_name")
	public String acqDriverName;

	@ExternalValue("acq.server_host")
	public String acqServerHost;
	
	@ExternalValue("experiment.digital_port_juice_trigger_delay")
	public long digitalPortJuiceTriggerDelay;

	@Bean(lazy = Lazy.FALSE)
	public XperConfig xperConfig() {
		List<String> libs = new LinkedList<String>();
		libs.add("xper");
		if (acqDriverName.equalsIgnoreCase(DAQ_COMEDI)) {
			libs.add("xper-comedi");
		} else if (acqDriverName.equalsIgnoreCase(DAQ_NI)){
			libs.add("xper-ni");
		} else if (acqDriverName.equalsIgnoreCase(DAQ_NONE)){
			// Don't load any driver specific library.
		} else {
			throw new ExperimentSetupException("Acq driver " + acqDriverName + " not supported.");
		}
		XperConfig config = new XperConfig(baseConfig.nativeLibraryPath, libs);
		return config;
	}

	@Bean
	public SocketDataAcqServer dataAcqServer () {
		SocketDataAcqServer server = new SocketDataAcqServer();
		server.setHost(acqServerHost);
		server.setAcqDeviceController(acqDeviceController());
		server.setTimeServer(timeServer());
		return server;
	}
	
	@Bean
	public SocketDataAcqClient dataAcqClient () {
		SocketDataAcqClient client = new SocketDataAcqClient(acqServerHost);
		return client;
	}
	
	@Bean
	public DefaultAcqDeviceController acqDeviceController () {
		DefaultAcqDeviceController controller = new DefaultAcqDeviceController();
		AcqStreamingDevice device;
		if (acqDriverName.equalsIgnoreCase(DAQ_COMEDI)) {
			device = comediAnalogStreamingDevice();
		} else if (acqDriverName.equalsIgnoreCase(DAQ_NI)) {
			device = niAnalogStreamingDevice();
		} else {
			throw new ExperimentSetupException("Acq driver " + acqDriverName + " not supported.");
		}
		controller.setAcqDevice(device);
		controller.setDataBuffer(dataBuffer());
		controller.setDataFilterController(dataFilterController());
		controller.setDbUtil(baseConfig.dbUtil());
		controller.setLocalTimeUtil(baseConfig.localTimeUtil());
		controller.setDeviceBufferCount(acqDeviceBufferCount());
		controller.init();
		return controller;
	}
	
	@Bean
	public NiAnalogStreamingDevice niAnalogStreamingDevice() {
		NiAnalogStreamingDevice device = new NiAnalogStreamingDevice();
		device.setBufferSize(acqDeviceBufferSize());
		device.setMasterFreqency(acqMasterFrequency());
		device.setDeviceString(acqDevice());
		device.setInputChannels(acqChannelFactory().getNiAcqChannels());
		return device;
	}
	
	@Bean
	public ComediAnalogStreamingDevice comediAnalogStreamingDevice() {
		ComediAnalogStreamingDevice device = new ComediAnalogStreamingDevice();
		device.setBufferSize(acqDeviceBufferSize());
		device.setMasterFreqency(acqMasterFrequency());
		device.setDeviceString(acqDevice());
		device.setInputChannels(acqChannelFactory().getComediAcqChannels());
		return device;
	}
	
	@Bean
	public AcqChannelFactory acqChannelFactory() {
		AcqChannelFactory factory = new AcqChannelFactory();
		factory.setDataBuffer(dataBuffer());
		factory.setVariableContainer(baseConfig.systemVariableContainer());
		factory.init();
		return factory;
	}
	
	@Bean
	public DefaultDataFilterController dataFilterController() {
		DefaultDataFilterController controller = new DefaultDataFilterController();
		controller.setChannelFilterList(acqChannelFactory().getAcqChannelFilter());
		return controller;
	}
	
	@Bean
	public DatabaseDataBuffer dataBuffer () {
		DatabaseDataBuffer buffer = new DatabaseDataBuffer ();
		buffer.setBlockSize(acqDataBlockSize());
		buffer.setDbUtil(baseConfig.dbUtil());
		buffer.setLocalTimeUtil(baseConfig.localTimeUtil());
		return buffer;
	}

	@Bean
	public SocketTimeServer timeServer() {
		SocketTimeServer server = new SocketTimeServer ();
		server.setHost(acqServerHost);
		server.setLocalTimeUtil(baseConfig.localTimeUtil());
		return server;
	}
	
	@Bean
	public SocketTimeClient timeClient() {
		SocketTimeClient client = new SocketTimeClient(acqServerHost);
		return client;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public String acqDevice () {
		return baseConfig.systemVariableContainer().get("acq_device", 0);
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double acqMasterFrequency () {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("acq_master_frequency", 0));
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer acqDeviceBufferSize () {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("acq_device_buffer_size", 0));
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer acqDataBlockSize () {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("acq_data_block_size", 0));
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer acqDeviceBufferCount () {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("acq_device_buffer_count", 0));
	}

}