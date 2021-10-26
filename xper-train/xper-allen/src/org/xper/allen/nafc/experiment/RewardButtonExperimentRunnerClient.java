package org.xper.allen.nafc.experiment;

import org.xper.experiment.ExperimentRunnerClient;

public class RewardButtonExperimentRunnerClient extends ExperimentRunnerClient{

public RewardButtonExperimentRunnerClient(String host) {
		super(host);
		// TODO Auto-generated constructor stub
	}

public void reward(){
	doCommand(RewardButtonExperimentRunner.REWARD);
}
	
}
