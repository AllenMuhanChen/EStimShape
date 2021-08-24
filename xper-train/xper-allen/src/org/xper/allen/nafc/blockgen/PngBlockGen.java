package org.xper.allen.nafc.blockgen;

import java.io.File;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Random;

import org.xper.Dependency;
import org.xper.allen.nafc.experiment.RewardPolicy;
import org.xper.allen.specs.GaussSpec;
import org.xper.allen.specs.NAFCStimSpecSpec;
import org.xper.allen.util.AllenDbUtil;
import org.xper.allen.util.AllenXMLUtil;
import org.xper.drawing.Coordinates2D;
import org.xper.exception.VariableNotFoundException;
import org.xper.time.TimeUtil;

import com.mchange.v1.util.ArrayUtils;


public class PngBlockGen {
	@Dependency
	AllenDbUtil dbUtil;
	@Dependency
	TimeUtil globalTimeUtil;
	@Dependency
	AllenXMLUtil xmlUtil;
	
	/**
	 * Selects visual stimuli randomly from stimTypes
	 */
	Random r = new Random();
	
	public PngBlockGen() {
	}
	
	
	long genId = 1;
	
	
	public void generate() { //
		//SETTINGS
		File folder = new File("/home/r2_allen/Documents/pngs");
		File[] fileArray = folder.listFiles();
		
		//PARAMETERS
		int numTrials = 100;
		Coordinates2D[] targetEyeWinCoords = {new Coordinates2D(-10, 0), new Coordinates2D(10,0)};	
		int numChoices = targetEyeWinCoords.length;
		double[] targetEyeWinSize = {5, 5};
		long[] eStimObjData = {1};
		RewardPolicy rewardPolicy = RewardPolicy.LIST;
		
		//GENERATION
		try {
			genId = 0;
			//genId = dbUtil.readReadyGenerationInfo().getGenId() + 1;
		} catch (VariableNotFoundException e) {
			dbUtil.writeReadyGenerationInfo(genId, 0);
		}
		for (File file : fileArray){
			if (file.isFile()) {

				
		    }
		}
		for (int i = 0; i < numTrials; i++) {
			//SAMPLE
			long sampleId = globalTimeUtil.currentTimeMicros();
			long taskId = sampleId;
			int randomSampleIndex = r.nextInt(fileArray.length);
			dbUtil.writeStimObjData(sampleId, fileArray[randomSampleIndex].getAbsolutePath(), "sample: " + randomSampleIndex);
			
			//CHOICE
			int correctChoice = r.nextInt(numChoices);
			int[] rewardList = {correctChoice};
			
			//Handling shuffling & removing Match from possible distractors
			int matchIndex = randomSampleIndex;
			File[] distractorArray = fileArray;
			List<File> distractorList = new ArrayList<File>(Arrays.asList(distractorArray));
			distractorList.remove(matchIndex);
			Collections.shuffle(distractorList);
			
			//Step through all of the choices. If the index corresponds to the randomly decided correct choice index, write path of match.
			//else, write the path of one of the distractors. The paths of the distractor is found through stepping through shuffled list of distractors
			int distractorIndex = 0;
			long[] choiceId = new long[numChoices];
			for (int j = 0; j < numChoices; j++) {
				choiceId[j] = sampleId + j + 1;
				
				if (j==correctChoice){
					dbUtil.writeStimObjData(choiceId[j], fileArray[randomSampleIndex].getAbsolutePath(), "choice " + j);
				}
				else{
					dbUtil.writeStimObjData(choiceId[j], distractorList.get(distractorIndex).getAbsolutePath(), "choice " + j);
					distractorIndex += 1;
				}
			}
	
			//stimSpec just needs Ids, not the path of the pngs themselves. Pngs are stored in StimObjData
			NAFCStimSpecSpec stimSpec = new NAFCStimSpecSpec(targetEyeWinCoords, targetEyeWinSize, sampleId, choiceId, eStimObjData, rewardPolicy, rewardList);
			
			String spec = stimSpec.toXml();
			System.out.println(spec);
			
			dbUtil.writeStimSpec(taskId, stimSpec.toXml());
			dbUtil.writeTaskToDo(taskId, taskId, -1, genId);
		
		}
		dbUtil.updateReadyGenerationInfo(genId, numTrials);
		System.out.println("Done Generating...");
		return;
		
	}

	public AllenDbUtil getDbUtil() {
		return dbUtil;
	}

	public void setDbUtil(AllenDbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}
	public TimeUtil getGlobalTimeUtil() {
		return globalTimeUtil;
	}

	public void setGlobalTimeUtil(TimeUtil globalTimeUtil) {
		this.globalTimeUtil = globalTimeUtil;
	}

	public AllenXMLUtil getXmlUtil() {
		return xmlUtil;
	}

	public void setXmlUtil(AllenXMLUtil xmlUtil) {
		this.xmlUtil = xmlUtil;
	}

}
