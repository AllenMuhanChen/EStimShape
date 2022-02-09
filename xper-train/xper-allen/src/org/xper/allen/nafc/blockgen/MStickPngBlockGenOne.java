package org.xper.allen.nafc.blockgen;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;
import java.util.Random;
import java.util.concurrent.ThreadLocalRandom;
import java.util.stream.IntStream;

import org.xper.Dependency;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.MetricMorphParams;
import org.xper.allen.drawing.png.ImageDimensions;
import org.xper.allen.nafc.experiment.RewardPolicy;
import org.xper.allen.specs.NAFCStimSpecSpec;
import org.xper.allen.specs.PngSpec;
import org.xper.allen.util.AllenDbUtil;
import org.xper.allen.util.AllenXMLUtil;
import org.xper.drawing.Coordinates2D;
import org.xper.exception.VariableNotFoundException;
import org.xper.time.TimeUtil;
import org.xper.utils.RGBColor;

/**
 * Generate MSticks, convert to Png. 
 * @author r2_allen
 *
 */
public class MStickPngBlockGenOne{
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
	@Dependency
	AllenPNGMaker pngMaker;
	@Dependency
	double maxImageDimensionDegrees;
	@Dependency
	String experimentImageFolderPath;
	/**
	 * Selects visual stimuli randomly from stimTypes
	 */
	Random r = new Random();
	
	/**
	 *  Generate trials where:
	 *  Sample: Generated matchstick from a randomly generated limb
	 *  Match:  Morphed version of sample where starter limb is slightly morphed (metric morph)
	 *  Distractors: completely random match sticks. 
	 */	

	public MStickPngBlockGenOne() {
	}

	long genId = 1;
	List<Long> ids = new ArrayList<Long>();

	public void generate(int[] trialTypes, int[] trialNums,
			double sampleScaleUpperLim, double sampleRadiusLowerLim, 
			double sampleRadiusUpperLim, double eyeWinSize, 
			double choiceRadiusLowerLim, double choiceRadiusUpperLim, 
			double distractorDistanceLowerLim, 
			double distractorDistanceUpperLim,
			double distractorScaleUpperLim, double metricMorphMagnitude) { //


		
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

		//INITIALIZING LISTS TO HOLD MATCH STICK OBJECTS
		List<AllenMatchStick> objs_base = new ArrayList<AllenMatchStick>();
		List<AllenMatchStick> objs_sample = new ArrayList<AllenMatchStick>();
		List<AllenMatchStick> objs_match = new ArrayList<AllenMatchStick>();
		List<ArrayList<AllenMatchStick>> objs_distractor = new ArrayList<ArrayList<AllenMatchStick>>();
		for(int i=0; i<numTrials; i++){
			int numChoices = trialTypeList.get(i);
			objs_base.add(new AllenMatchStick());
			objs_sample.add(new AllenMatchStick());
			objs_match.add(new AllenMatchStick());
			objs_distractor.add(new ArrayList<AllenMatchStick>());
			for(int j=0; j<numChoices-1; j++){
				objs_distractor.get(i).add(new AllenMatchStick());
			}
		}

		//LOAD METRIC MORPH PARAMETERS
		MetricMorphParams mmp = new MetricMorphParams();
		//orientation (along along mAxis)
		mmp.orientationFlag = true;
		mmp.orientationMagnitude.percentChangeLowerBound = 0.02;
		mmp.orientationMagnitude.percentChangeUpperBound = 0.04;
		mmp.orientationMagnitude.range = 2*Math.PI;
		//rotation (rotation along tangent axis)
		mmp.rotationFlag = true;
		mmp.rotationMagnitude.percentChangeLowerBound = 0.15;
		mmp.rotationMagnitude.percentChangeUpperBound = 0.3;
		mmp.rotationMagnitude.range = 2*Math.PI;
		//length (arcLength of mAxis Arc)
		mmp.lengthFlag = true;
		mmp.lengthMagnitude.percentChangeLowerBound = 0.15;
		mmp.lengthMagnitude.percentChangeUpperBound = 0.3;
		mmp.lengthMagnitude.range = sampleScaleUpperLim;
		//size (uniform scale of radProfile)
		mmp.sizeFlag = true;
		mmp.sizeMagnitude.percentChangeLowerBound = 0.15;
		mmp.sizeMagnitude.percentChangeUpperBound = 0.3;
		mmp.sizeMagnitude.range = 3;
		//curvature
		mmp.curvatureFlag = true;
		mmp.curvatureMagnitude.percentChangeLowerBound = 0.15;
		mmp.curvatureMagnitude.percentChangeUpperBound = 0.3;
		mmp.curvatureMagnitude.range = mmp.lengthMagnitude.range*6;
		//position
		mmp.positionFlag = true;
		mmp.positionMagnitude.percentChangeLowerBound = 0.15;
		mmp.positionMagnitude.percentChangeUpperBound = 0.3;
		mmp.positionMagnitude.range = 1; //TODO: TINKER WITH THIS VALUE
		//radProfile
		mmp.radProfileJuncFlag = true;
		mmp.radProfileJuncMagnitude.percentChangeLowerBound = 0.15;
		mmp.radProfileJuncMagnitude.percentChangeUpperBound = 0.3;
		mmp.radProfileEndMagnitude.range = 
		//
		mmp.radProfileMidFlag = true;
		mmp.radProfileMidMagnitude.percentChangeLowerBound = 0.15;
		mmp.radProfileMidMagnitude.percentChangeUpperBound = 0.3;
		mmp.radProfileEndFlag = true;
		mmp.radProfileEndMagnitude.percentChangeLowerBound = 0.15;
		mmp.radProfileEndMagnitude.percentChangeUpperBound = 0.3;
		//
		
		
		
		
		//GENERATION
		try {
			/**
			 * Gen ID is important for xper to be able to load new tasks on the fly. It will only do so if the generation Id is upticked. 
			 */
			genId = dbUtil.readReadyGenerationInfo().getGenId() + 1;
		} catch (VariableNotFoundException e) {
			dbUtil.writeReadyGenerationInfo(genId, 0);
		}

		int nSuccess = 0;
		for (int i = 0; i < numTrials; i++) {
			int numChoices = trialTypeList.get(i);


			//GENERATE BASE, SAMPLE, AND MATCH WITHIN LOOP TO MAKE SURE IF 
			//GENERATE MATCH/SAMPLE FAILS, WE START OVER STARTING AT BASE
			boolean tryagain = true;
			int nTries = 0;
			while (tryagain){
				boolean sampleSuccess = false;
				boolean matchSuccess = false;

				//BASE: GENERATING MATCHSTICK
				setProperties(objs_base.get(i));
				objs_base.get(i).genMatchStickRand();
				int randomLeaf = objs_base.get(i).chooseRandLeaf();
				

				//SAMPLE: GENERATING MATCHSTICSK
				System.out.println("In Sample");
				//System.out.println("Trying to Generate Sample. Try: " + tries);
				setProperties(objs_sample.get(i));
				sampleSuccess = objs_sample.get(i).genMatchStickFromLeaf(randomLeaf, objs_base.get(i));
				//tries++;
				if(!sampleSuccess){
					objs_sample.set(i, new AllenMatchStick());
				}

				
				//MATCH: GENERATING MATCHSTICK
				if(sampleSuccess){

					int leafToMorphIndx = objs_sample.get(i).chooseRandLeaf(); 
					//boolean maintainTangent = true;

					System.out.println("In Match");
					try{
						setProperties(objs_match.get(i));
						matchSuccess = objs_match.get(i).genMetricMorphedLeafMatchStick(leafToMorphIndx, objs_sample.get(i), mmp);
					} catch(Exception e){
						matchSuccess = false;
					}
					if(!matchSuccess){
						objs_match.set(i, new AllenMatchStick());
					}

				}



				if(sampleSuccess & matchSuccess){
					tryagain = false;
					nSuccess++;
					System.out.println("SUCCESS!: " + nSuccess);
				}
				else{
					tryagain = true;
					nTries++;
					System.out.println("TRYING AGAIN: " + nTries + " tries.");
				}
			}

			//GENERATING DISTRACTORS
			for(int j=0; j<numChoices-1; j++){
				setProperties(objs_distractor.get(i).get(j));
				objs_distractor.get(i).get(j).genMatchStickRand();
			}

			//GENERATING STIM-OBJ SPECS & WRITE TO DB
			//Determine Ids
			long sampleId = globalTimeUtil.currentTimeMicros();
			long matchId = sampleId + 1;
			List<Long> distractorIds = new LinkedList<Long>();
			for (int j=0; j<objs_distractor.get(i).size(); j++){
				distractorIds.add(matchId + j + 1);
			}


			//GENERATE PNGS
			List<AllenMatchStick> objs = new LinkedList<AllenMatchStick>();
			//objs.add(objs_base.get(i));
			objs.add(objs_sample.get(i));
			objs.add(objs_match.get(i));
			objs.addAll(objs_distractor.get(i));

			List<Long> ids = new LinkedList<Long>();
			//ids.add(sampleId-1);
			ids.add(sampleId);
			ids.add(matchId);
			ids.addAll(distractorIds);
			pngMaker.createAndSavePNGsfromObjs(objs, ids);

			//SPECIFYING LOCATION
			Coordinates2D sampleCoords = randomWithinRadius(sampleRadiusLowerLim, sampleRadiusUpperLim);
			DistancedDistractorsUtil ddUtil = new DistancedDistractorsUtil(numChoices, choiceRadiusLowerLim, choiceRadiusUpperLim, distractorDistanceLowerLim,  distractorDistanceUpperLim);
			ArrayList<Coordinates2D> distractorsCoords = (ArrayList<Coordinates2D>) ddUtil.getDistractorCoordsAsList();
			Coordinates2D matchCoords = ddUtil.getMatchCoords();

			//SAMPLE
			long taskId = sampleId;
			PngSpec sampleSpec = new PngSpec();
			sampleSpec.setPath(experimentImageFolderPath+"/"+ids.get(0)+".png");
			sampleSpec.setxCenter(sampleCoords.getX());
			sampleSpec.setyCenter(sampleCoords.getY());
			ImageDimensions sampleDimensions = new ImageDimensions(sampleScaleUpperLim, sampleScaleUpperLim);
			sampleSpec.setImageDimensions(sampleDimensions);
			dbUtil.writeStimObjData(sampleId, sampleSpec.toXml(), "sample");

			//
			long[] choiceIds = new long[numChoices];

			//MATCH
			PngSpec matchSpec = new PngSpec();
			matchSpec.setPath(experimentImageFolderPath+"/"+ids.get(1)+".png");
			matchSpec.setxCenter(matchCoords.getX());
			matchSpec.setyCenter(matchCoords.getY());
			ImageDimensions matchDimensions = new ImageDimensions(sampleScaleUpperLim, sampleScaleUpperLim);
			matchSpec.setImageDimensions(matchDimensions);
			dbUtil.writeStimObjData(matchId, matchSpec.toXml(), "Match");
			choiceIds[0] = matchId;

			//DISTRACTORS
			List<PngSpec> distractorSpec = new ArrayList<PngSpec>();
			for(int j=0; j<numChoices-1; j++){
				distractorSpec.add(j, new PngSpec());
				distractorSpec.get(j).setPath(experimentImageFolderPath+"/"+ids.get(j+2)+".png");
				distractorSpec.get(j).setxCenter(distractorsCoords.get(j).getX());
				distractorSpec.get(j).setyCenter(distractorsCoords.get(j).getY());
				ImageDimensions distractorDimensions = new ImageDimensions(distractorScaleUpperLim, distractorScaleUpperLim);
				distractorSpec.get(j).setImageDimensions(distractorDimensions);
				dbUtil.writeStimObjData(distractorIds.get(j), distractorSpec.get(j).toXml(), "Distractor");
				choiceIds[j+1] = distractorIds.get(j);
			}

			//GENERATING & WRITING STIM-SPEC TO DB
			//targetEyeWinCoords
			List<Coordinates2D> targetEyeWinCoords = new LinkedList<Coordinates2D>();
			targetEyeWinCoords.add(matchCoords);
			targetEyeWinCoords.addAll(distractorsCoords);
			//targetEyeWinSize
			double[] targetEyeWinSizeArray = new double[numChoices];
			for(int j=0; j < numChoices; j++) {
				targetEyeWinSizeArray[j] = eyeWinSize;
			}
			//eStimObjData
			long[] eStimObjData = {1};
			//rewardPolicy
			RewardPolicy rewardPolicy = RewardPolicy.LIST;
			//rewardList - Correct answer should always be 0 (the first choice)
			int[] rewardList = {0};

			//WRITE SPEC
			NAFCStimSpecSpec stimSpec = new NAFCStimSpecSpec(targetEyeWinCoords.toArray(new Coordinates2D[0]), targetEyeWinSizeArray, sampleId, choiceIds, eStimObjData, rewardPolicy, rewardList);

			dbUtil.writeStimSpec(taskId, stimSpec.toXml());
			dbUtil.writeTaskToDo(taskId, taskId, -1, genId);


		}
		dbUtil.updateReadyGenerationInfo(genId, numTrials);
		System.out.println("Done Generating...");

		return;
	}

	/**
	 * It is imperative that these properties are set before the object is generated/is smoothized.
	 * @param obj
	 */
	private void setProperties(AllenMatchStick obj) {
		//OBJECT PROPERTIES
		//SETTING SIZES 
		/**
		 * With this strategy of scale setting, we set our maxImageDimensionDegrees to
		 * twice about what we want the actual size of our stimuli to be. Then we try to draw the stimuli
		 * to be approx half the size. 
		 */
		double scale = maxImageDimensionDegrees/2;
		double minScale = maxImageDimensionDegrees/4;
		obj.setScale(minScale, scale);
		
		//CONTRAST
		double contrast = 1;
		obj.setContrast(contrast);
		
		//COLOR
		RGBColor white = new RGBColor(1,1,1);
		obj.setStimColor(white);
		
		//TEXTURE
		obj.setTextureType("SHADE");

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

		/**
		 * 
		 * @return
		 */
		public List<Coordinates2D> getDistractorCoordsAsList(){

			return distractor_coords;
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

	public AllenPNGMaker getPngMaker() {
		return pngMaker;
	}

	public void setPngMaker(AllenPNGMaker pngMaker) {
		this.pngMaker = pngMaker;
	}

	public double getMaxImageDimensionDegrees() {
		return maxImageDimensionDegrees;
	}

	public void setMaxImageDimensionDegrees(double maxImageDimensionDegrees) {
		this.maxImageDimensionDegrees = maxImageDimensionDegrees;
	}

	public String getExperimentImageFolderPath() {
		return experimentImageFolderPath;
	}

	public void setExperimentImageFolderPath(String experimentImageFolderPath) {
		this.experimentImageFolderPath = experimentImageFolderPath;
	}

}
