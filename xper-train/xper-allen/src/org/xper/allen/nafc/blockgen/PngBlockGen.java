package org.xper.allen.nafc.blockgen;

import java.awt.Dimension;
import java.io.File;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Random;
import java.util.concurrent.ThreadLocalRandom;
import java.util.stream.IntStream;

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

import static org.xper.allen.nafc.blockgen.NAFCCoordinateAssigner.randomCoordsWithinRadii;


public class PngBlockGen extends AbstractTrialGenerator{
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
	 * Specify the alpha value of all distractors. Sample is automatically 1. 
	 * 
	 * This code is written pretty sloppily. Copy and pasted big block of code to handle choice spec in two different ways. 
	 */
	public PngBlockGen() {
	}


	long genId = 1;


	public void generate(int[] trialTypes, int[] trialNums, 
			double width, double height, double sampleRadiusLowerLim, 
			double sampleRadiusUpperLim, double eyeWinSize, 
			double choiceRadiusLowerLim, double choiceRadiusUpperLim, 
			double alphaLowerLim, double alphaUpperLim, double distractorDistanceLowerLim, 
			double distractorDistanceUpperLim, double distractorScaleLowerLim, 
			double distractorScaleUpperLim ) { //

		experimentPngPath = experimentPngPath+"/";
		//FILEPATH
		File folder = new File(generatorPngPath);
		File[] fileArray = folder.listFiles();

		//INTERMIXING TYPES OF TRIALS
		int numTrials = IntStream.of(trialNums).sum(); //Sum all elements of trialNums
		List<Integer>trialTypeList = new ArrayList<Integer>(); //Type = number of choices
		int numTypes = trialTypes.length;
		for (int i=0; i < numTypes; i++){ //For every type of trial
			for (int j=0; j < trialNums[i]; j++){ //for every trial of that type
				trialTypeList.add(trialTypes[i]); //add the number of choices to the list
			}
		}
		Collections.shuffle(trialTypeList);
		//FIXED-PARAMETERS
		//int numTrials = 100;
		//SAMPLE
		ImageDimensions sampleDimensions = new ImageDimensions(width,height);
		double[] sampleRadiusLims = {sampleRadiusLowerLim, sampleRadiusUpperLim}; 
		//CHOICES
		RewardPolicy rewardPolicy = RewardPolicy.LIST;
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
			Coordinates2D sampleLocation = randomCoordsWithinRadii(sampleRadiusLims[0], sampleRadiusLims[1]);
			String experimentPath = experimentPngPath + fileArray[randomSampleIndex].getName();
			PngSpec sampleSpec = new PngSpec(sampleLocation.getX(), sampleLocation.getY(), sampleDimensions, experimentPngPath + fileArray[randomSampleIndex].getName());
			dbUtil.writeStimObjData(sampleId, sampleSpec.toXml(), "sample");

			//CHOICE
			int numChoices = trialTypeList.get(i);
			int correctChoice = r.nextInt(numChoices);
			int[] rewardList = {correctChoice};
			//			ImageDimensions[] choiceDimensions = new ImageDimensions[numChoices];
			//			for (int j = 0; j<numChoices; j++){
			//				choiceDimensions[j] = sampleDimensions;
			//			}

			//Handling shuffling & removing Match from possible distractors
			int matchIndex = randomSampleIndex;
			File[] distractorArray = fileArray;
			List<File> distractorList = new ArrayList<File>(Arrays.asList(distractorArray));
			distractorList.remove(matchIndex);
			Collections.shuffle(distractorList);

			//EyewinCoords of target and target location identical
			DistancedDistractorsUtil ddUtil = new DistancedDistractorsUtil(numChoices, choiceRadiusLowerLim, choiceRadiusUpperLim, distractorDistanceLowerLim,  distractorDistanceUpperLim);
			Coordinates2D matchEyeWinCoords = new Coordinates2D();
			ArrayList<Coordinates2D> distractorsEyeWinCoords = new ArrayList<Coordinates2D>();
			
			//Coordinates2D[] targetEyeWinCoords = new Coordinates2D[]{};
			//targetEyeWinCoords = distancedDistractorsEquidistantRandomChoices(choiceRadiusLowerLim,choiceRadiusUpperLim,numChoices, distractorList);
			
			//Step through all of the choices. If the index corresponds to the randomly decided correct choice index, write path of match.
			//else, write the path of one of the distractors. The paths of the distractor is found through stepping through shuffled list of distractors
			int distractorIndex = 0;
			long[] choiceId = new long[numChoices];

			ArrayList<Coordinates2D> targetEyeWinCoords = new ArrayList<Coordinates2D>();
			for (int j = 0; j < numChoices; j++) {
				choiceId[j] = sampleId + j + 1;
				
				if (j==correctChoice){
					//Size
					ImageDimensions matchDimensions = new ImageDimensions(width, height);

					//Distance
					matchEyeWinCoords = ddUtil.getMatchCoords();

					PngSpec choiceSpec = new PngSpec(matchEyeWinCoords.getX(), matchEyeWinCoords.getY(), matchDimensions, experimentPngPath + fileArray[randomSampleIndex].getName());
					dbUtil.writeStimObjData(choiceId[j], choiceSpec.toXml(), "choice " + j + "; " + "match");
				
					targetEyeWinCoords.add(matchEyeWinCoords); //to be converted to array later to pass as targetEyeWindow
				}
				else{
					//Alpha
					double randomAlpha = inclusiveRandomDouble(alphaLowerLim, alphaUpperLim);

					//Size
					double randomScale = inclusiveRandomDouble(distractorScaleLowerLim, distractorScaleUpperLim);
					ImageDimensions distractorDimensions = new ImageDimensions();
					distractorDimensions = new ImageDimensions(width*randomScale, height*randomScale);
					
					//Distance
					Coordinates2D distractorEyeWinCoords = ddUtil.getDistractorCoords();
					distractorsEyeWinCoords.add(distractorEyeWinCoords);
					
					PngSpec choiceSpec = new PngSpec(distractorEyeWinCoords.getX(), distractorEyeWinCoords.getY(),distractorDimensions, experimentPngPath + distractorList.get(distractorIndex).getName(), randomAlpha);
					dbUtil.writeStimObjData(choiceId[j], choiceSpec.toXml(), "choice " + j + "; " + "distractor");
					distractorIndex += 1;
					
					targetEyeWinCoords.add(distractorEyeWinCoords);
				}
			}


			//stimSpec just needs Ids, not the path of the pngs themselves. Pngs are stored in StimObjData
			Coordinates2D[] targetEyeWinCoordsArray = targetEyeWinCoords.toArray(new Coordinates2D[0]);
		
			ArrayList<Double> targetEyeWinSize = new ArrayList<Double>();
			for(Coordinates2D choice:targetEyeWinCoordsArray){
				targetEyeWinSize.add(eyeWinSize);
			}
			double[] targetEyeWinSizeArray = new double[targetEyeWinSize.size()];
			for(int j=0; j < targetEyeWinSize.size(); j++) {
				targetEyeWinSizeArray[j] = targetEyeWinSize.get(j);
			}
			
			NAFCStimSpecSpec stimSpec = new NAFCStimSpecSpec(targetEyeWinCoordsArray, targetEyeWinSizeArray, sampleId, choiceId, eStimObjData, rewardPolicy, rewardList);
			String spec = stimSpec.toXml();
			//System.out.println(spec);

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
