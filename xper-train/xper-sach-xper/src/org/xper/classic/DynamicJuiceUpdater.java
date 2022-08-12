package org.xper.classic;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.classic.vo.TrialContext;
import org.xper.experiment.SystemVariableContainer;
import org.xper.juice.DynamicJuice;

public class DynamicJuiceUpdater implements TrialEventListener {
	static Logger logger = Logger.getLogger(DynamicJuiceUpdater.class);

	@Dependency
	SystemVariableContainer variableContainer;
	@Dependency
	DynamicJuice juice;

	public void eyeInBreak(long timestamp, TrialContext context) {
	}

	public void eyeInHoldFail(long timestamp, TrialContext context) {
	}

	public void fixationPointOn(long timestamp, TrialContext context) {
	}

	public void fixationSucceed(long timestamp, TrialContext context) {
	}

	public void initialEyeInFail(long timestamp, TrialContext context) {
	}

	public void initialEyeInSucceed(long timestamp, TrialContext context) {
	}

	public void trialComplete(long timestamp, TrialContext context) {
	}

	public void trialInit(long timestamp, TrialContext context) {
	}
	
	public void trialStart(long timestamp, TrialContext context) {
	}

	public void trialStop(long timestamp, TrialContext context) {
		variableContainer.refresh();
		double reward = Double.parseDouble(variableContainer.get(
				"xper_juice_reward_length", 0));
		juice.setReward(reward);
		logger.info("Juice reward set to " + reward);
	}

	public DynamicJuice getJuice() {
		return juice;
	}

	public void setJuice(DynamicJuice juice) {
		this.juice = juice;
	}

	public SystemVariableContainer getVariableContainer() {
		return variableContainer;
	}

	public void setVariableContainer(SystemVariableContainer variableContainer) {
		this.variableContainer = variableContainer;
	}
}
