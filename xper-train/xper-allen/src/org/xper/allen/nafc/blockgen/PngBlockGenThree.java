package org.xper.allen.nafc.blockgen;

import java.awt.Dimension;
import java.io.File;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Random;
import java.util.concurrent.ThreadLocalRandom;

import org.xper.Dependency;
import org.xper.allen.drawing.png.ImageDimensions;
import org.xper.allen.nafc.experiment.RewardPolicy;
import org.xper.allen.specs.NAFCStimSpecSpec;
import org.xper.allen.specs.PngSpec;
import org.xper.allen.util.AllenDbUtil;
import org.xper.allen.util.AllenXMLUtil;
import org.xper.drawing.Coordinates2D;
import org.xper.exception.VariableNotFoundException;
import org.xper.time.TimeUtil;



public class PngBlockGenThree{
	@Dependency
	AllenDbUtil dbUtil;
	@Dependency
	TimeUtil globalTimeUtil;
	@Dependency
	AllenXMLUtil xmlUtil;
	@Dependency
	String generatorPngPath;
	@Dependency
	String experimentPngPath;
	/**
	 * Selects visual stimuli randomly from stimTypes
	 */
	Random r = new Random();
	/**
	 * Generate trials with sample in random location within specified disc region,
	 * as well as 1-2 choices randomly within another specified disc region.   
	 * 
	 * Specify the number of trials with just a single choice, and the number of trials with two choices.  
	 * 
	 * This code is written pretty sloppily. Copy and pasted big block of code to handle choice spec in two different ways. 
	 */
	public PngBlockGenThree() {
	}
	
	
	long genId = 1;
	
	
	public void generate(int numSingleChoiceTrials, int numDoubleChoiceTrials, double width, double height, double sampleRadiusLowerLim, double sampleRadiusUpperLim, double eyeWinSize, double choiceRadiusLowerLim, double choiceRadiusUpperLim ) { //
		experimentPngPath = experimentPngPath+"/";
		//FILEPATH
		File folder = new File(generatorPngPath);
		File[] fileArray = folder.listFiles();
		
		//INTERMIXING SINGLE & DOUBLE CHOICES
		int numTrials = numSingleChoiceTrials + numDoubleChoiceTrials;
		List<Boolean>isSingleList = new ArrayList<Boolean>();
		for (int i=0; i<numSingleChoiceTrials; i++){ //populate list
			isSingleList.add(true);
		}
		for (int i=0; i<numDoubleChoiceTrials; i++){ //populate list
			isSingleList.add(false);
		}
		Collections.shuffle(isSingleList);
		//FIXED-PARAMETERS
		//int numTrials = 100;
			//SAMPLE
		ImageDimensions sampleDimensions = new ImageDimensions(width,height);
		double[] sampleRadiusLims = {sampleRadiusLowerLim, sampleRadiusUpperLim}; 
			//CHOICES
		RewardPolicy rewardPolicy = RewardPolicy.LIST;
		double[] targetEyeWinSize = {eyeWinSize, eyeWinSize};
		long[] eStimObjData = {1};
		
		//GENERATION
		try {
			/**
			 * Gen ID is important for xper to be able to load new tasks on the fly. It will only do so if the generation Id is upticked. 
			 */
			genId = dbUtil.readReadyGenerationInfo().getGenId() + 1;
		} catch (VariableNotFoundException e) {
			dbUtil.writeReadyGenerationInfo(genId, 0);
		}
		for (int i = 0; i < numTrials; i++) {
			//SAMPLE
			long sampleId = globalTimeUtil.currentTimeMicros();
			long taskId = sampleId;
			int randomSampleIndex = r.nextInt(fileArray.length);
			Coordinates2D sampleLocation = randomWithinRadius(sampleRadiusLims[0], sampleRadiusLims[1]);
			String experimentPath = experimentPngPath + fileArray[randomSampleIndex].getName();
			PngSpec sampleSpec = new PngSpec(sampleLocation.getX(), sampleLocation.getY(), sampleDimensions, experimentPngPath + fileArray[randomSampleIndex].getName());
			dbUtil.writeStimObjData(sampleId, sampleSpec.toXml(), "sample");
			
			//CHOICE
			if(isSingleList.get(i)){ //If this a single choice trial
				int numChoices = 1;
				int correctChoice = r.nextInt(1);
				int[] rewardList = {correctChoice};
				ImageDimensions[] choiceDimensions = new ImageDimensions[numChoices];
				for (int j = 0; j<numChoices; j++){
				    choiceDimensions[j] = sampleDimensions;
				}
				//EyewinCoords of target and target location identical
				Coordinates2D[] targetEyeWinCoords = new Coordinates2D[]{};
				targetEyeWinCoords = equidistantRandomChoices(choiceRadiusLowerLim,choiceRadiusUpperLim,numChoices);
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
						PngSpec choiceSpec = new PngSpec(targetEyeWinCoords[j].getX(), targetEyeWinCoords[j].getY(), choiceDimensions[j], experimentPngPath + fileArray[randomSampleIndex].getName());
						dbUtil.writeStimObjData(choiceId[j], choiceSpec.toXml(), "choice " + j + "; " + "match");
					}
					else{
						PngSpec choiceSpec = new PngSpec(targetEyeWinCoords[j].getX(), targetEyeWinCoords[j].getY(),choiceDimensions[j], experimentPngPath + distractorList.get(distractorIndex).getName());
						dbUtil.writeStimObjData(choiceId[j], choiceSpec.toXml(), "choice " + j + "; " + "distractor");
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
			else{ //if this is a double choice trial
				int numChoices=2;
				int correctChoice = r.nextInt(2);
				int[] rewardList = {correctChoice};
				ImageDimensions[] choiceDimensions = new ImageDimensions[numChoices];
				for (int j = 0; j<numChoices; j++){
				    choiceDimensions[j] = sampleDimensions;
				}
				//EyewinCoords of target and target location identical
				Coordinates2D[] targetEyeWinCoords = new Coordinates2D[]{};
				targetEyeWinCoords = equidistantRandomChoices(choiceRadiusLowerLim,choiceRadiusUpperLim,numChoices);
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
						PngSpec choiceSpec = new PngSpec(targetEyeWinCoords[j].getX(), targetEyeWinCoords[j].getY(), choiceDimensions[j], experimentPngPath + fileArray[randomSampleIndex].getName());
						dbUtil.writeStimObjData(choiceId[j], choiceSpec.toXml(), "choice " + j + "; " + "match");
					}
					else{
						PngSpec choiceSpec = new PngSpec(targetEyeWinCoords[j].getX(), targetEyeWinCoords[j].getY(),choiceDimensions[j], experimentPngPath + distractorList.get(distractorIndex).getName());
						dbUtil.writeStimObjData(choiceId[j], choiceSpec.toXml(), "choice " + j + "; " + "distractor");
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
		}
		dbUtil.updateReadyGenerationInfo(genId, numTrials);
		System.out.println("Done Generating...");
		return;
		
	}
	
	private static Coordinates2D randomChoice(double lowerRadiusLim, double upperRadiusLim){
		return randomWithinRadius(lowerRadiusLim, upperRadiusLim);
		
	}
	/**
	 * Specifies locations choices such that they are equidistant (Angular) from each other and organized in a ring around the center. 
	 * For example, if there are two choices, they will be 180 degrees apart. If three choices, they will be 120 degrees apart. 
	 * @param lowerRadiusLim
	 * @param upperRadiusLim
	 * @param numChoices
	 * @return
	 */
	private static Coordinates2D[] equidistantRandomChoices(double lowerRadiusLim, double upperRadiusLim, int numChoices){
		Coordinates2D[] output = new Coordinates2D[numChoices];
		Double[] angles = new Double[numChoices];
		Double[] radii = new Double[numChoices];
		
		angles[0] = ThreadLocalRandom.current().nextDouble() * 2 * Math.PI;
		radii[0] = Math.sqrt(ThreadLocalRandom.current().nextDouble()) * (upperRadiusLim-lowerRadiusLim) + lowerRadiusLim;
		output[0] = polarToCart(radii[0], angles[0]);
		
		if (numChoices==1){
			return output;
		}
		else{
			double step = 2 * Math.PI / numChoices;
			for (int i=1; i < numChoices; i++){
				angles[i] = angles[i-1] + step; //step the angle
				radii[i] = radii[i-1]; //keep radius the same
				output[i] = polarToCart(radii[i], angles[i]); //polar to cartesian
			}
			return output;
		}
		
		
	}
	private static double inclusiveRandomDouble(double val1, double val2) {
		if (val2>val1){
			return ThreadLocalRandom.current().nextDouble(val1, val2);
		}
		else {
			return val1;
		}

	}
	
	private static Coordinates2D randomWithinRadius(double lowerLim, double upperLim) {
		
		double r = Math.sqrt(ThreadLocalRandom.current().nextDouble()) * (upperLim-lowerLim) + lowerLim;
		double theta = ThreadLocalRandom.current().nextDouble() * 2 * Math.PI;
		
		Coordinates2D output = polarToCart(r, theta);
		return output;
	}
	
	private static Coordinates2D polarToCart(double r, double theta){
		Coordinates2D output = new Coordinates2D(); 
		double x = 0 + r * Math.cos(theta);
		double y = 0 + r * Math.sin(theta);
		output.setX(x);
		output.setY(y);
		return output;
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

	public String getGeneratorPngPath() {
		return generatorPngPath;
	}

	public void setGeneratorPngPath(String generatorPngPath) {
		this.generatorPngPath = generatorPngPath;
	}

	public String getExperimentPngPath() {
		return experimentPngPath;
	}

	public void setExperimentPngPath(String experimentPngPath) {
		this.experimentPngPath = experimentPngPath;
	}

}
