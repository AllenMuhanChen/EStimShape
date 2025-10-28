package org.xper.allen.nafc.blockgen.psychometric;

import java.util.ArrayList;
import java.util.List;

import org.xper.allen.nafc.blockgen.NAFC;
import org.xper.allen.nafc.blockgen.NAFCTrialParameters;
import org.xper.allen.nafc.experiment.RewardPolicy;
import org.xper.allen.specs.NAFCStimSpecSpec;
import org.xper.allen.util.AllenDbUtil;
import org.xper.drawing.Coordinates2D;

public class NAFCStimSpecWriter {

    protected String stimType = "None";
    protected Long taskId;
    protected AllenDbUtil dbUtil;
    protected NAFCTrialParameters trialParameters; //input
    protected NAFC<Coordinates2D> coords;
    protected int numChoices;
    protected NAFC<Long> stimObjIds;
    protected RewardPolicy rewardPolicy;
	protected int[] rewardList;

	private NAFCStimSpecWriter(String stimType, Long taskId, AllenDbUtil dbUtil,
							   NAFCTrialParameters trialParameters, NAFC<Coordinates2D> coords, int numChoices,
							   NAFC<Long> stimObjIds, RewardPolicy rewardPolicy, int[] rewardList) {
		super();
		this.stimType = stimType;
		this.taskId = taskId;
		this.dbUtil = dbUtil;
		this.trialParameters = trialParameters;
		this.coords = coords;
		this.numChoices = numChoices;
		this.stimObjIds = stimObjIds;
		this.eStimObjData = new long[]{1};
		this.rewardPolicy = rewardPolicy;
		this.rewardList = rewardList;
	}

	private NAFCStimSpecWriter(String stimType, Long taskId, AllenDbUtil dbUtil,
							   NAFCTrialParameters trialParameters, NAFC<Coordinates2D> coords, int numChoices,
							   NAFC<Long> stimObjIds, long[] eStimObjData, RewardPolicy rewardPolicy, int[] rewardList) {
		super();
		this.stimType = stimType;
		this.taskId = taskId;
		this.dbUtil = dbUtil;
		this.trialParameters = trialParameters;
		this.coords = coords;
		this.numChoices = numChoices;
		this.stimObjIds = stimObjIds;
		this.eStimObjData = eStimObjData;
		this.rewardPolicy = rewardPolicy;
		this.rewardList = rewardList;
	}

	private long[] eStimObjData;

	private List<Coordinates2D> targetEyeWinCoords = new ArrayList<Coordinates2D>();
	private double[] targetEyeWinSizes;
	private long[] choiceIds;

    public NAFCStimSpecWriter() {
    }

    public static NAFCStimSpecWriter createForNoEStim(String stimType, Long taskId, AllenDbUtil dbUtil,
													  NAFCTrialParameters trialParameters, NAFC<Coordinates2D> coords, int numChoices,
													  NAFC<Long> stimObjIds, RewardPolicy rewardPolicy, int[] rewardList) {
		return new NAFCStimSpecWriter(stimType, taskId, dbUtil, trialParameters, coords, numChoices, stimObjIds, rewardPolicy, rewardList);
	}

	public static NAFCStimSpecWriter createForEStim(String stimType, Long taskId, AllenDbUtil dbUtil,
													NAFCTrialParameters trialParameters, NAFC<Coordinates2D> coords, int numChoices,
													NAFC<Long> stimObjIds, long[] eStimObjData, RewardPolicy rewardPolicy, int[] rewardList) {
		return new NAFCStimSpecWriter(stimType, taskId, dbUtil, trialParameters, coords, numChoices, stimObjIds, eStimObjData, rewardPolicy, rewardList);
	}

	public void writeStimSpec() {
		assignEyeWindowCoordinates();
		assignTargetEyeWindowSizes();
		assignChoiceIds();
		writeSpec();
	}

    protected void assignEyeWindowCoordinates() {
		targetEyeWinCoords.add(coords.getMatch());
		targetEyeWinCoords.addAll(coords.getAllDistractors());
	}

    protected void assignTargetEyeWindowSizes() {
		targetEyeWinSizes = new double[numChoices];
		for(int j=0; j < numChoices; j++) {
			targetEyeWinSizes[j] = trialParameters.getEyeWinRadius();
		}
	}

	/**
	 * choiceId along with rewardPolicy is matched with rewardList ids to determine if a trial is correct
	 * or incorrect.
	 */
    protected void assignChoiceIds() {
		choiceIds = new long[numChoices];
		choiceIds[0] = stimObjIds.getMatch();
		for (int distractorIdIndx=0; distractorIdIndx<stimObjIds.getAllDistractors().size(); distractorIdIndx++) {
			choiceIds[distractorIdIndx+1] = stimObjIds.getAllDistractors().get(distractorIdIndx);
		}
	}

	protected void writeSpec() {
		NAFCStimSpecSpec stimSpec = new NAFCStimSpecSpec(
				stimType,
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