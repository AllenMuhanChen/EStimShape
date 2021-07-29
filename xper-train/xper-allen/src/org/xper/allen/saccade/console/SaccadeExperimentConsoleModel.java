package org.xper.allen.saccade.console;

import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Set;
import java.util.Map.Entry;
import java.util.concurrent.atomic.AtomicReference;

import org.xper.Dependency;
import org.xper.acq.mock.SocketSamplingDeviceServer;
import org.xper.allen.saccade.db.vo.SaccadeTrialStatistics;
import org.xper.classic.TrialExperimentMessageHandler;
import org.xper.classic.vo.TrialStatistics;
import org.xper.console.ExperimentConsoleModel;
import org.xper.console.ExperimentMessageReceiver;
import org.xper.drawing.Coordinates2D;
import org.xper.exception.ExperimentSetupException;
import org.xper.experiment.ExperimentRunnerClient;
import org.xper.eye.mapping.MappingAlgorithm;
import org.xper.eye.vo.EyeDeviceIdChannelPair;
import org.xper.eye.vo.EyeDeviceReading;
import org.xper.eye.vo.EyeWindow;
import org.xper.time.TimeUtil;

public class SaccadeExperimentConsoleModel extends ExperimentConsoleModel {
	@Dependency
	SaccadeExperimentMessageHandler messageHandler;
	
	public SaccadeTrialStatistics getTrialStatistics () {
		SaccadeTrialStatistics stat = messageHandler.getTrialStatistics();
		return stat;
	}
	
	public void setMessageHandler(SaccadeExperimentMessageHandler msghandler) {
		this.messageHandler = msghandler;
	}
	
	public Set<String> getEyeDeviceIds () {
		return messageHandler.getEyeDeviceIds();
	}
	
	public Set<Entry<String, EyeDeviceReading>> getEyeDeviceReading () {
		return messageHandler.getEyeDeviceReadingEntries();
	}

	
	public Coordinates2D getEyeZero (String id) {
		Coordinates2D eyeZero = messageHandler.getEyeZeroByDeviceId(id);
		return eyeZero;
	}
	
	public double getData(int channel) {
		EyeDeviceIdChannelPair deviceChannel = getChannelMap().get(channel);
		Coordinates2D eyeZero = messageHandler
				.getEyeZeroByDeviceId(deviceChannel.getId());
		Coordinates2D degree = getEyePositionInDegree().get();
		MappingAlgorithm algorithm = getEyeMappingAlgorithm().get(deviceChannel.getId());
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

	public SaccadeExperimentMessageHandler getMessageHandler() {
		return messageHandler;
	}

	
	public EyeWindow getEyeWindow () {
		EyeWindow window = messageHandler.getEyeWindow();
		return window;
	}
}
