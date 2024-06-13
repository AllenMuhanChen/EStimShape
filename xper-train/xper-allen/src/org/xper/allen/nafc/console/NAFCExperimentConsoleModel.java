package org.xper.allen.nafc.console;

import java.lang.reflect.Method;
import java.util.Map.Entry;
import java.util.Set;

import org.xper.Dependency;
import org.xper.allen.nafc.experiment.RewardButtonExperimentRunnerClient;
import org.xper.allen.nafc.message.NAFCExperimentMessageHandler;
import org.xper.console.ExperimentConsoleModel;
import org.xper.drawing.Coordinates2D;
import org.xper.exception.ExperimentSetupException;
import org.xper.eye.mapping.MappingAlgorithm;
import org.xper.eye.vo.EyeDeviceIdChannelPair;
import org.xper.eye.vo.EyeDeviceReading;
import org.xper.eye.vo.EyeWindow;

public class NAFCExperimentConsoleModel extends ExperimentConsoleModel{
		@Dependency
		NAFCExperimentMessageHandler messageHandler;

		@Dependency
		NAFCExperimentMessageReceiver messageReceiver;

		@Dependency
		RewardButtonExperimentRunnerClient experimentRunnerClient;

		public void reward(){
			experimentRunnerClient.reward();
			System.out.println("Juice delivered because of console command ");
		}

		public NAFCTrialStatistics getNAFCTrialStatistics () {
			NAFCTrialStatistics stat = (NAFCTrialStatistics) messageHandler.getNAFCTrialStatistics();
			return stat;
		}

		public void start () {
			getEyePositionInDegree().set(new Coordinates2D(0,0));
			messageReceiver.start();
			if (getSamplingServer() != null) {
				getSamplingServer().start();
			}
		}

		public void resume () {
			experimentRunnerClient.resume();
		}

		public void pause () {
			experimentRunnerClient.pause();
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
		public void setMessageHandler(NAFCExperimentMessageHandler msghandler) {
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

		public NAFCExperimentMessageHandler getMessageHandler() {
			return messageHandler;
		}


		public EyeWindow getEyeWindow () {
			EyeWindow window = messageHandler.getEyeWindow();
			return window;
		}

		public NAFCExperimentMessageReceiver getNAFCMessageReceiver() {
			return messageReceiver;
		}

		public void setMessageReceiver(NAFCExperimentMessageReceiver messageReceiver) {
			this.messageReceiver = messageReceiver;
		}

		public RewardButtonExperimentRunnerClient getExperimentRunnerClient() {
			return experimentRunnerClient;
		}

		public void setExperimentRunnerClient(RewardButtonExperimentRunnerClient experimentRunnerClient) {
			this.experimentRunnerClient = experimentRunnerClient;
		}

}