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



public class PngBlockGenFour{
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
	public PngBlockGenFour() {
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
			Coordinates2D sampleLocation = randomWithinRadius(sampleRadiusLims[0], sampleRadiusLims[1]);
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

	private static Coordinates2D randomChoice(double lowerRadiusLim, double upperRadiusLim){
		return randomWithinRadius(lowerRadiusLim, upperRadiusLim);

	}
	
	/**
	 * Class to aid in creating equally radially spaced choices, but allow the distractors to be further from center. 
	 * @author r2_allen
	 *
	 */
	public class DistancedDistractorsUtil {
		int numChoices;
		double lowerRadiusLim;
		double upperRadiusLim;
		double distractorDistanceLowerLim;
		double distractorDistanceUpperLim;
		
		Double[] distractor_angles;
		Double[] distractor_radii;
		ArrayList<Coordinates2D> distractor_coords;
		
		double match_angle;
		double match_radii;
		Coordinates2D match_coords;
		
		public DistancedDistractorsUtil(int numChoices, double lowerRadiusLim, double upperRadiusLim, double distractorDistanceLowerLim, double distractorDistanceUpperLim){
			this.numChoices = numChoices;
			this.lowerRadiusLim = lowerRadiusLim;
			this.upperRadiusLim = upperRadiusLim;
			this.distractorDistanceLowerLim = distractorDistanceLowerLim;
			this.distractorDistanceUpperLim = distractorDistanceUpperLim;
			
			distractor_angles = new Double[numChoices-1];
			distractor_radii = new Double[numChoices-1];
			distractor_coords = new ArrayList<Coordinates2D>();
			
			double distractorDistance = inclusiveRandomDouble(distractorDistanceLowerLim, distractorDistanceUpperLim);
			
			match_angle = ThreadLocalRandom.current().nextDouble() * 2 * Math.PI;
			double baseRadii = Math.sqrt(ThreadLocalRandom.current().nextDouble()) * (upperRadiusLim-lowerRadiusLim) + lowerRadiusLim;
			match_radii = baseRadii;
			match_coords = polarToCart(match_radii, match_angle);
			
			double step = 2 * Math.PI / numChoices;
			for (int i=0; i < numChoices-1; i++){
				if(i==0){
					distractor_angles[i] = match_angle + step; //step the angle
				}
				else{
					distractor_angles[i] = distractor_angles[i-1] + step;
				}
				distractor_radii[i] = baseRadii + distractorDistance; //keep radius the same
				distractor_coords.add(polarToCart(distractor_radii[i], distractor_angles[i])); //polar to cartesian
			}
		}
		
		public Coordinates2D getMatchCoords(){
			return match_coords;
		}
		
		/**
		 * get the coords of one of the distractors, then remove it 
		 * @return
		 */
		public Coordinates2D getDistractorCoords(){
			Coordinates2D output = distractor_coords.get(0);
			distractor_coords.remove(0);
			
			return output;
		}
		
		
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
