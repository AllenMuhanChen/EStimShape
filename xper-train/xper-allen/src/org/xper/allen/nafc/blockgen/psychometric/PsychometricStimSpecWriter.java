package org.xper.allen.nafc.blockgen.psychometric;

import java.util.ArrayList;
import java.util.List;

import org.xper.allen.nafc.experiment.RewardPolicy;
import org.xper.allen.specs.NAFCStimSpecSpec;
import org.xper.allen.util.AllenDbUtil;
import org.xper.drawing.Coordinates2D;

public class PsychometricStimSpecWriter {

	Long taskId;
	AllenDbUtil dbUtil;
	NoisyTrialParameters trialParameters; //input
	Psychometric<Coordinates2D> coords;
	int numChoices;
	Psychometric<Long> stimObjIds;

	public PsychometricStimSpecWriter(Long taskId, AllenDbUtil dbUtil,
			NoisyTrialParameters trialParameters, Psychometric<Coordinates2D> coords, int numChoices,
			Psychometric<Long> stimObjIds) {
		super();
		this.taskId = taskId;
		this.dbUtil = dbUtil;
		this.trialParameters = trialParameters;
		this.coords = coords;
		this.numChoices = numChoices;
		this.stimObjIds = stimObjIds;
	}

	private long[] eStimObjData;
	private RewardPolicy rewardPolicy;
	private int[] rewardList;
	private List<Coordinates2D> targetEyeWinCoords = new ArrayList<Coordinates2D>();
	private double[] targetEyeWinSizes;
	private long[] choiceIds;
	
	public void writeStimSpec() {
		assignEyeWindowCoordinates();
		assignTargetEyeWindowSizes();
		writeEStimObjData();
		assignChoiceIds();
		writeSpec();
	}

	private void assignEyeWindowCoordinates() {
		targetEyeWinCoords.add(coords.getMatch());
		targetEyeWinCoords.addAll(coords.getAllDistractors());
	}

	private void assignTargetEyeWindowSizes() {
		targetEyeWinSizes = new double[numChoices];
		for(int j=0; j < numChoices; j++) {
			targetEyeWinSizes[j] = trialParameters.getEyeWinSize();
		}
	}
	
	private void writeEStimObjData() {
		eStimObjData = new long[] {1};
		rewardPolicy = RewardPolicy.LIST;
		rewardList = new int[] {0};
	}
	
	/**
	 * choiceId along with rewardPolicy is matched with rewardList ids to determine if a trial is correct
	 * or incorrect. 
	 */
	private void assignChoiceIds() {
		choiceIds = new long[numChoices];
		choiceIds[0] = stimObjIds.getMatch();
		for (int distractorIdIndx=0; distractorIdIndx<stimObjIds.getAllDistractors().size(); distractorIdIndx++) {
			choiceIds[distractorIdIndx+1] = stimObjIds.getAllDistractors().get(distractorIdIndx);
		}
	}
	
	private void writeSpec() {
		NAFCStimSpecSpec stimSpec = new NAFCStimSpecSpec(
				targetEyeWinCoords.toArray(new Coordinates2D[0]),
				targetEyeWinSizes,
				stimObjIds.getSample(),
				choiceIds,
				eStimObjData,
				rewardPolicy,
				rewardList);
		dbUtil.writeStimSpec(taskId, stimSpec.toXml(), trialParameters.toXml());
	}

}
