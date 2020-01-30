package org.xper.console;

import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Set;
import java.util.Map.Entry;
import java.util.concurrent.atomic.AtomicReference;

import org.xper.Dependency;
import org.xper.acq.device.AcqSamplingDevice;
import org.xper.acq.mock.SocketSamplingDeviceServer;
import org.xper.classic.TrialExperimentMessageHandler;
import org.xper.classic.vo.TrialStatistics;
import org.xper.drawing.Coordinates2D;
import org.xper.exception.ExperimentSetupException;
import org.xper.experiment.ExperimentRunnerClient;
import org.xper.eye.mapping.MappingAlgorithm;
import org.xper.eye.vo.EyeDeviceIdChannelPair;
import org.xper.eye.vo.EyeDeviceReading;
import org.xper.eye.vo.EyeWindow;
import org.xper.time.TimeUtil;

public class ExperimentConsoleModel implements AcqSamplingDevice {
	
	/**
	 * Map channel number to input array index.
	 */ 
	@Dependency
	HashMap<Integer, EyeDeviceIdChannelPair> channelMap;
	
	@Dependency
	HashMap<String, MappingAlgorithm> eyeMappingAlgorithm;
	
	@Dependency
	TrialExperimentMessageHandler messageHandler;
	
	@Dependency
	ExperimentMessageReceiver messageReceiver;
	
	@Dependency
	SocketSamplingDeviceServer samplingServer;
	@Dependency
	ExperimentRunnerClient experimentRunnerClient;
	@Dependency
	TimeUtil localTimeUtil;
	
	/**
	 * monkey eye voltage.
	 */ 
	AtomicReference<Coordinates2D> eyePositionInDegree = new AtomicReference<Coordinates2D>();
	
	public void resume () {
		experimentRunnerClient.resume();
	}
	
	public void pause () {
		experimentRunnerClient.pause();
	}
	
	public void start () {
		eyePositionInDegree.set(new Coordinates2D(0,0));
		messageReceiver.start();
		if (samplingServer != null) {
			samplingServer.start();
		}
	}
	
	public void stop () {
		try {
			experimentRunnerClient.stop();
			messageReceiver.stop();
			if (samplingServer != null) {
				samplingServer.stop();
			}
		} catch (Exception e) {
			e.printStackTrace();
		}
	}
	
	public Set<String> getEyeDeviceIds () {
		return messageHandler.getEyeDeviceIds();
	}
	
	public EyeWindow getEyeWindow () {
		EyeWindow window = messageHandler.getEyeWindow();
		return window;
	}
	
	public Set<Entry<String, EyeDeviceReading>> getEyeDeviceReading () {
		return messageHandler.getEyeDeviceReadingEntries();
	}
	
	public TrialStatistics getTrialStatistics () {
		TrialStatistics stat = messageHandler.getTrialStatistics();
		return stat;
	}
	
	public Coordinates2D getEyeZero (String id) {
		Coordinates2D eyeZero = messageHandler.getEyeZeroByDeviceId(id);
		return eyeZero;
	}
	
	public void setEyePosition (Coordinates2D degree) {
		eyePositionInDegree.set(degree);
	}

	public double getData(int channel) {
		EyeDeviceIdChannelPair deviceChannel = channelMap.get(channel);
		Coordinates2D eyeZero = messageHandler
				.getEyeZeroByDeviceId(deviceChannel.getId());
		Coordinates2D degree = eyePositionInDegree.get();
		MappingAlgorithm algorithm = eyeMappingAlgorithm.get(deviceChannel.getId());
		Coordinates2D volt = algorithm.degree2Volt(degree, eyeZero);

		try {
			Method m = degree.getClass().getDeclaredMethod(
					"get" + deviceChannel.getChannel());
			double v = (Double) m.invoke(volt);
			return v;
		} catch (Exception e) {
			throw new ExperimentSetupException(e);
		}
	}

	public long scan() {
		return localTimeUtil.currentTimeMicros();
	}
	
	public HashMap<Integer, EyeDeviceIdChannelPair> getChannelMap() {
		return channelMap;
	}

	public void setChannelMap(HashMap<Integer, EyeDeviceIdChannelPair> channelMap) {
		this.channelMap = channelMap;
	}

	public HashMap<String, MappingAlgorithm> getEyeMappingAlgorithm() {
		return eyeMappingAlgorithm;
	}

	public void setEyeMappingAlgorithm(
			HashMap<String, MappingAlgorithm> eyeMappingAlgorithm) {
		this.eyeMappingAlgorithm = eyeMappingAlgorithm;
	}
	
	public TrialExperimentMessageHandler getMessageHandler() {
		return messageHandler;
	}

	public void setMessageHandler(TrialExperimentMessageHandler messageHandler) {
		this.messageHandler = messageHandler;
	}
	
	public ExperimentMessageReceiver getMessageReceiver() {
		return messageReceiver;
	}

	public void setMessageReceiver(ExperimentMessageReceiver messageReceiver) {
		this.messageReceiver = messageReceiver;
	}

	public SocketSamplingDeviceServer getSamplingServer() {
		return samplingServer;
	}

	public void setSamplingServer(SocketSamplingDeviceServer samplingServer) {
		this.samplingServer = samplingServer;
	}

	public ExperimentRunnerClient getExperimentRunnerClient() {
		return experimentRunnerClient;
	}

	public void setExperimentRunnerClient(
			ExperimentRunnerClient experimentRunnerClient) {
		this.experimentRunnerClient = experimentRunnerClient;
	}

	public TimeUtil getLocalTimeUtil() {
		return localTimeUtil;
	}

	public void setLocalTimeUtil(TimeUtil localTimeUtil) {
		this.localTimeUtil = localTimeUtil;
	}
	
}
