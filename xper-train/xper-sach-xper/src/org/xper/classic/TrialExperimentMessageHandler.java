package org.xper.classic;

import java.util.HashMap;
import java.util.Set;
import java.util.Map.Entry;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

import org.xper.Dependency;
import org.xper.classic.vo.TrialStatistics;
import org.xper.console.ExperimentMessageHandler;
import org.xper.db.vo.BehMsgEntry;
import org.xper.drawing.Coordinates2D;
import org.xper.eye.vo.EyeDeviceMessage;
import org.xper.eye.vo.EyeDeviceReading;
import org.xper.eye.vo.EyeWindow;
import org.xper.eye.vo.EyeWindowMessage;
import org.xper.eye.vo.EyeZeroMessage;

public class TrialExperimentMessageHandler implements ExperimentMessageHandler {
	/**
	 * id => Volt
	 */
	@Dependency
	ConcurrentHashMap<String, EyeDeviceReading> eyeDeviceReading = new ConcurrentHashMap<String, EyeDeviceReading>();
	@Dependency
	AtomicReference<EyeWindow> eyeWindow = new AtomicReference<EyeWindow>();
	@Dependency
	ConcurrentHashMap<String, Coordinates2D> eyeZero = new ConcurrentHashMap<String, Coordinates2D>();
	
	AtomicBoolean fixationOn = new AtomicBoolean(false);
	AtomicBoolean inTrial = new AtomicBoolean(false);
	AtomicBoolean eyeIn = new AtomicBoolean(false);
	AtomicReference<TrialStatistics> trialStat = new AtomicReference<TrialStatistics>();
	
	public TrialExperimentMessageHandler() {
		trialStat.set(new TrialStatistics());
	}
	
	public boolean handleMessage(BehMsgEntry msg) {
			if ("EyeDeviceMessage".equals(msg.getType())) {
				handleEyeDeviceMessage(msg);
				return true;
			} else if ("FixationPointOn".equals(msg.getType())){
				fixationOn.set(true);
				return true;
			} else if ("EyeInBreak".equals(msg.getType()) ||
					"EyeInHoldFail".equals(msg.getType()) ||
					"InitialEyeInFail".equals(msg.getType()) ||
					"TrialComplete".equals(msg.getType())) {
				fixationOn.set(false);
				return true;
			} else if ("EyeWindowMessage".equals(msg.getType())) {
				handleEyeWindowMessage(msg);
				return true;
			} else if ("EyeZeroMessage".equals(msg.getType())) {
				handleEyeZeroMessage(msg);
				return true;
			} else if ("TrialStatistics".equals(msg.getType())) {
				handleTrialStatistics(msg);
				return true;
			} else if ("TrialInit".equals(msg.getType())) {
				inTrial.set(true);
				return true;
			} else if ("TrialStop".equals(msg.getType())) {
				inTrial.set(false);
				return true;
			} else if ("EyeInEvent".equals(msg.getType())) {
				eyeIn.set(true);
				return true;
			} else if ("EyeOutEvent".equals(msg.getType())) {
				eyeIn.set(false);
				return true;
			} else {
				return false;
			}
	}

	public boolean isEyeIn() {
		return eyeIn.get();
	}

	public boolean isInTrial() {
		return inTrial.get();
	}

	public boolean isFixationOn() {
		return fixationOn.get();
	}

	public TrialStatistics getTrialStatistics() {
		return trialStat.get();
	}

	void handleEyeDeviceMessage(BehMsgEntry ent) {
		EyeDeviceMessage m = EyeDeviceMessage.fromXml(ent.getMsg());
		eyeDeviceReading.put(m.getId(), new EyeDeviceReading(m.getVolt(), m
				.getDegree()));
	}

	void handleEyeWindowMessage(BehMsgEntry ent) {
		EyeWindowMessage m = EyeWindowMessage.fromXml(ent.getMsg());
		eyeWindow.set(new EyeWindow(m.getCenter(), m.getSize()));
	}

	void handleEyeZeroMessage(BehMsgEntry ent) {
		EyeZeroMessage m = EyeZeroMessage.fromXml(ent.getMsg());
		eyeZero.put(m.getId(), m.getZero());
	}

	void handleTrialStatistics(BehMsgEntry ent) {
		trialStat.set(TrialStatistics.fromXml(ent.getMsg()));
	}

	public Coordinates2D getEyeZeroByDeviceId(String id) {
		return eyeZero.get(id);
	}

	public void setEyeZero(HashMap<String, Coordinates2D> eyeZero) {
		this.eyeZero.putAll(eyeZero);
	}

	public Set<Entry<String, EyeDeviceReading>> getEyeDeviceReadingEntries() {
		return eyeDeviceReading.entrySet();
	}

	public void setEyeDeviceReading(
			HashMap<String, EyeDeviceReading> eyeDeviceReading) {
		this.eyeDeviceReading.putAll(eyeDeviceReading);
	}
	
	public Set<String> getEyeDeviceIds () {
		return eyeZero.keySet();
	}

	public EyeWindow getEyeWindow() {
		return eyeWindow.get();
	}

	public void setEyeWindow(EyeWindow eyeWindow) {
		this.eyeWindow.set(eyeWindow);
	}
}
