package org.xper.allen.nafc.blockgen;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Random;
import java.util.concurrent.ThreadLocalRandom;
import java.util.stream.IntStream;

import org.xper.Dependency;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.png.ImageDimensions;
import org.xper.allen.nafc.experiment.RewardPolicy;
import org.xper.allen.specs.AllenMStickSpec;
import org.xper.allen.specs.NAFCStimSpecSpec;
import org.xper.allen.specs.PngSpec;
import org.xper.allen.util.AllenDbUtil;
import org.xper.allen.util.AllenXMLUtil;
import org.xper.drawing.Coordinates2D;
import org.xper.exception.VariableNotFoundException;
import org.xper.time.TimeUtil;



public class MStickBlockGenOne{
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
	 *  Generate trials where:
	 *  Sample: Generated matchstick from a randomly generated limb
	 *  Match:  Morphed version of sample where starter limb is replaced (just needs to make an approximate but not identical stimulus)
	 *  Distractors: completely random match sticks. 
	 */
	public MStickBlockGenOne() {
	}

	long genId = 1;

	public void generate(int[] trialTypes, int[] trialNums,
			double sampleScaleLowerLim, double sampleScaleUpperLim, double sampleRadiusLowerLim, 
			double sampleRadiusUpperLim, double eyeWinSize, 
			double choiceRadiusLowerLim, double choiceRadiusUpperLim, 
			double distractorDistanceLowerLim, 
			double distractorDistanceUpperLim, double distractorScaleLowerLim, 
			double distractorScaleUpperLim) { //

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
			for(int j=0; j<numChoices; j++){
				objs_distractor.get(i).add(new AllenMatchStick());
			}
		}
		

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
			int numChoices = trialTypeList.get(i);
			//BASE: GENERATING MATCHSTICK
			objs_base.get(i).genMatchStickRand();
			int randomLeaf = objs_base.get(i).chooseRandLeaf();
			
			//SAMPLE: GENERATING MATCHSTICSK
			objs_sample.get(i).genMatchStickFromLeaf(randomLeaf, objs_base.get(i));
			
			//CHOICES: GENERATING MATCHSTICKS
			//GENERATING MATCH
			int leafToMorphIndx = 1; //The randomly chosen leaf before should be the first component
			boolean maintainTangent = true;
			objs_match.get(i).genMorphedLeafMatchStick(leafToMorphIndx, objs_sample.get(i), maintainTangent);
			//GENERATING DISTRACTORS
			for(int j=0; j<numChoices-1; j++){
				objs_distractor.get(i).get(j).genMatchStickRand();
			}

			//SPECIFYING LOCATION
			Coordinates2D sampleEyeWinCoords = randomWithinRadius(sampleRadiusLowerLim, sampleRadiusUpperLim);
			DistancedDistractorsUtil ddUtil = new DistancedDistractorsUtil(numChoices, choiceRadiusLowerLim, choiceRadiusUpperLim, distractorDistanceLowerLim,  distractorDistanceUpperLim);
			ArrayList<Coordinates2D> distractorsEyeWinCoords = (ArrayList<Coordinates2D>) ddUtil.getDistractorCoordsAsList();
			Coordinates2D matchEyeWinCoords = ddUtil.getMatchCoords();
			objs_sample.get(i).centerShapeAtPoint(-1, sampleEyeWinCoords); //specifying -1 automatically finds the best tube
			objs_match.get(i).centerShapeAtPoint(-1, matchEyeWinCoords);
			for(int j=0; j<numChoices-1; j++){
				objs_distractor.get(i).get(j).centerShapeAtPoint(-1, distractorsEyeWinCoords.get(j));
			}
			
			//SPECIFYING SIZE
			objs_sample.get(i).setScale(sampleScaleLowerLim, sampleScaleUpperLim);
			objs_match.get(i).setScale(sampleScaleLowerLim, sampleScaleUpperLim);
			for(int j=0; j<numChoices-1; j++){
				objs_distractor.get(i).get(j).setScale(distractorScaleLowerLim, distractorScaleUpperLim);
			}
			
			//GENERATING SPECS
			//SAMPLE
			long sampleId = globalTimeUtil.currentTimeMicros();
			long taskId = sampleId;
			AllenMStickSpec sampleSpec = new AllenMStickSpec();
			sampleSpec.setMStickInfo(objs_sample.get(i));
			dbUtil.writeStimObjData(sampleId, sampleSpec.toXml(), "sample");
			//MATCH
			AllenMStickSpec matchSpec = new AllenMStickSpec();
			List<AllenMStickSpec> distractorSpec = new ArrayList<AllenMStickSpec>();
			matchSpec.setMStickInfo(objs_match.get(i));
			//DISTRACTORS
			for(int j=0; j<numChoices-1; j++){
				distractorSpec.add(new AllenMStickSpec());
				distractorSpec.get(j).setMStickInfo(objs_distractor.get(i).get(j));
			}

			//WRITING STIM-OBJ SPECS TO DB
			long[] choiceIds = new long[numChoices];
			ArrayList<Coordinates2D> targetEyeWinCoords = new ArrayList<Coordinates2D>();
			long matchId = sampleId + 1; choiceIds[0] = matchId;
			dbUtil.writeStimObjData(matchId, matchSpec.toXml(), "Match");
			for(int j=0;j<numChoices-1;j++){
				dbUtil.writeStimObjData(matchId+j+1, distractorSpec.get(j).toXml(), "Distractor");
				choiceIds[j+1] = matchId+j+1;
			}
			
			//WRITING STIM-SPECS TO DB
			//targetEyeWinCoords
			targetEyeWinCoords.add(matchEyeWinCoords);
			targetEyeWinCoords.addAll(distractorsEyeWinCoords);
			//targetEyeWinSize
			double[] targetEyeWinSizeArray = new double[numChoices];
			for(int j=0; j < numChoices; j++) {
				targetEyeWinSizeArray[j] = eyeWinSize;
			}
			//eStimObjData
			long[] eStimObjData = {1};
			//rewardPolicy
			RewardPolicy rewardPolicy = RewardPolicy.LIST;
			//rewardList
			int[] rewardList = {0};
			
			NAFCStimSpecSpec stimSpec = new NAFCStimSpecSpec(targetEyeWinCoords.toArray(new Coordinates2D[0]), targetEyeWinSizeArray, sampleId, choiceIds, eStimObjData, rewardPolicy, rewardList);

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

}
