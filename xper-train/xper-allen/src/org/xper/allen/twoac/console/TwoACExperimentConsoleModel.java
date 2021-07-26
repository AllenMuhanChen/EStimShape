package org.xper.allen.twoac.console;

import java.lang.reflect.Method;
import java.util.Set;
import java.util.Map.Entry;

import org.xper.Dependency;
import org.xper.allen.saccade.console.SaccadeExperimentMessageHandler;
import org.xper.allen.saccade.db.vo.SaccadeTrialStatistics;
import org.xper.console.ExperimentConsoleModel;
import org.xper.drawing.Coordinates2D;
import org.xper.exception.ExperimentSetupException;
import org.xper.eye.mapping.MappingAlgorithm;
import org.xper.eye.vo.EyeDeviceIdChannelPair;
import org.xper.eye.vo.EyeDeviceReading;
import org.xper.eye.vo.EyeWindow;

public class TwoACExperimentConsoleModel extends ExperimentConsoleModel{
		@Dependency
		TwoACExperimentMessageHandler messageHandler;
		
		public SaccadeTrialStatistics getTrialStatistics () {
			SaccadeTrialStatistics stat = (SaccadeTrialStatistics) messageHandler.getTrialStatistics();
			return stat;
		}
		
		public void setMessageHandler(TwoACExperimentMessageHandler msghandler) {
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

		public TwoACExperimentMessageHandler getMessageHandler() {
			return messageHandler;
		}

		
		public EyeWindow getEyeWindow () {
			EyeWindow window = messageHandler.getEyeWindow();
			return window;
		}
}
