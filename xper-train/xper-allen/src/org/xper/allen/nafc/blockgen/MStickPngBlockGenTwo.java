package org.xper.allen.nafc.blockgen;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;
import java.util.Random;
import java.util.concurrent.ThreadLocalRandom;
import java.util.stream.IntStream;

import javax.vecmath.Vector3d;

import org.xper.Dependency;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.metricmorphs.MetricMorphParameterGenerator;
import org.xper.allen.drawing.composition.metricmorphs.MetricMorphParams;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphParameterGenerator;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphParams;
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
public class MStickPngBlockGenTwo{
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
	String generatorSpecPath;
	@Dependency
	AllenPNGMaker pngMaker;
	@Dependency
	double maxImageDimensionDegrees;
	@Dependency
	QualitativeMorphParameterGenerator qmpGenerator;
	@Dependency
	MetricMorphParameterGenerator mmpGenerator;

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

	public MStickPngBlockGenTwo() {
	}

	long genId = 1;
	List<Long> ids = new ArrayList<Long>();

	public void generate(int[] numDistractors_types, int[] numDistractors_numTrials,
			double sampleScaleUpperLim, double sampleRadiusLowerLim, 
			double sampleRadiusUpperLim, double eyeWinSize, 
			double choiceRadiusLowerLim, double choiceRadiusUpperLim, 
			double distractorDistanceLowerLim, 
			double distractorDistanceUpperLim,
			double distractorScaleUpperLim, double metricMorphMagnitude,
			int[] numQMDistractors_types, int[] numQMDistractors_numTrials,
			int[] numCategoriesMorphed_types, int[] numCategoriesMorphed_numTrials) { //



		//INTERMIXING TYPES OF TRIALS
		//Distractor Num
		int numTrials = IntStream.of(numDistractors_numTrials).sum(); //Sum all elements of trialNums
		List<Integer>numDistractorsTrialList = new LinkedList<>(); //Type = number of choices
		int numDistractorTypes = numDistractors_types.length;
		for (int i=0; i < numDistractorTypes; i++){ //For every type of trial
			for (int j=0; j < numDistractors_numTrials[i]; j++){ //for every trial of that type
				numDistractorsTrialList.add(numDistractors_types[i]); //add the number of choices to the list
			}
		}
		Collections.shuffle(numDistractorsTrialList);

		//Number of QM Distractors
		if(IntStream.of(numQMDistractors_numTrials).sum() != numTrials) {
			throw new IllegalArgumentException("Total numDistractors_trialNums should match Total numDistractors_trialNums");
		}
		List<Integer>numQMDistractorsTrialList = new LinkedList<>();
		int numQMDistractorTypes = numQMDistractors_types.length;
		for(int i=0; i< numQMDistractorTypes; i++) {
			for(int j=0; j<numQMDistractors_numTrials[i]; j++) {
				numQMDistractorsTrialList.add(numQMDistractors_types[i]);
			}
		}
		Collections.shuffle(numQMDistractorsTrialList);

		//Number of Categories Morphed in QM
		if(IntStream.of(numCategoriesMorphed_numTrials).sum()!= numTrials) {
			throw new IllegalArgumentException("Total numCategoriesMorphed_numTrials should equal total numDistractors_trialNums");
		}
		List<Integer> numCategoriesMorphedTrialList = new LinkedList<>();
		int numCategoriesMorphedTypes = numCategoriesMorphed_types.length;
		for(int i=0; i<numCategoriesMorphedTypes;i++) {
			for(int j=0; j<numCategoriesMorphed_numTrials[i];j++) {
				numCategoriesMorphedTrialList.add(numCategoriesMorphed_types[i]);
			}
		}
		Collections.shuffle(numCategoriesMorphedTrialList);

		//INITIALIZING LISTS TO HOLD MATCH STICK OBJECTS
		List<AllenMatchStick> objs_base = new ArrayList<AllenMatchStick>();
		List<AllenMatchStick> objs_sample = new ArrayList<AllenMatchStick>();
		List<AllenMatchStick> objs_match = new ArrayList<AllenMatchStick>();
		List<ArrayList<AllenMatchStick>> objs_distractor = new ArrayList<ArrayList<AllenMatchStick>>();
		for(int i=0; i<numTrials; i++){
			int numChoices = numDistractorsTrialList.get(i)+1;
			objs_base.add(new AllenMatchStick());
			objs_sample.add(new AllenMatchStick());
			objs_match.add(new AllenMatchStick());
			objs_distractor.add(new ArrayList<AllenMatchStick>());
			for(int j=0; j<numChoices-1; j++){
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

		int nSuccess = 0;
		for (int i = 0; i < numTrials; i++) {
			int numQMDistractors = numQMDistractorsTrialList.get(i);
			int numRandDistractors = numDistractorsTrialList.get(i)-numQMDistractors;
			if(numRandDistractors<0) throw new IllegalArgumentException("There should not be less than 0 randDistractors");
			int numCategoriesMorphed = numCategoriesMorphedTrialList.get(i);


			//GENERATE BASE (leaf to morph + other limbs), SAMPLE, AND MATCH WITHIN LOOP TO MAKE SURE IF 
			//GENERATE MATCH/SAMPLE FAILS, WE START OVER STARTING AT BASE
			boolean tryagain = true;
			int nTries = 0;


			//SETTING MORPHS - we never want to change our morph because of a fail. Otherwise probability distribution of morph types will be skewed. 
			QualitativeMorphParams qmp = qmpGenerator.getQMP(numCategoriesMorphed);
			MetricMorphParams mmp = mmpGenerator.getMMP(sampleScaleUpperLim, metricMorphMagnitude);
			
			while (tryagain){
				boolean leafSuccess = false;
				boolean sampleSuccess = false;
				boolean matchSuccess = false;

				//BASE: GENERATING MATCHSTICK
				setProperties(objs_base.get(i));

				//VETTING AND CHOOSING RANDOM LEAF
				int randomLeaf=-1;
				int maxAttempts_leaf=5;
				int nTries_leaf=0;
				{ 
					while(nTries_leaf<maxAttempts_leaf) {
						System.out.println("In Leaf");
						objs_base.get(i).genMatchStickRand();
						randomLeaf = objs_base.get(i).chooseRandLeaf();
						leafSuccess = objs_base.get(i).vetLeaf(randomLeaf);
						if(!leafSuccess) {
							objs_base.set(i, new AllenMatchStick());
						} else {
							break;
						}
						nTries_leaf++;
					}
				}

				//SAMPLE: GENERATING MATCHSTICK FROM LEAF
				if(leafSuccess){
					int maxAttempts_sample=3;
					int nTries_sample=0;
					while(nTries_sample<maxAttempts_sample) {
						System.out.println("In Sample: attempt " + nTries_sample + " out of " + maxAttempts_sample);
						//System.out.println("Trying to Generate Sample. Try: " + tries);
						setProperties(objs_sample.get(i));
						sampleSuccess = objs_sample.get(i).genMatchStickFromLeaf(randomLeaf, objs_base.get(i));
						if(!sampleSuccess){
							objs_sample.set(i, new AllenMatchStick());
						}
						else {
							break;
						}
						nTries_sample++;
					}
				}

				//MATCH: GENERATING MATCHSTICK
				int leafToMorphIndx = objs_sample.get(i).getSpecialEndComp();
				if(sampleSuccess){
					int maxAttempts_match = 3;
					int nTries_match = 0;
					//int leafToMorphIndx = objs_sample.get(i).chooseRandLeaf(); 
					//boolean maintainTangent = true;
					while(nTries_match<maxAttempts_match) {
						System.out.println("In Match");
						try{
							setProperties(objs_match.get(i));
							//Generate MMPs here 
							matchSuccess = objs_match.get(i).genMetricMorphedLeafMatchStick(leafToMorphIndx, objs_sample.get(i), mmp);
						} catch(Exception e){
							e.printStackTrace();
							matchSuccess = false;
						}
						if(!matchSuccess){
							objs_match.set(i, new AllenMatchStick());
						} else {
							break;
						}
						nTries_match++;
					}
				}

				boolean qmDistractorsSuccess = false;
				if(matchSuccess) {
					System.out.println("Trying to Generate QM Distractors");
					Boolean[] qmDistractorSuccess;
					//GENERATING QM DISTRACTORS
					qmDistractorSuccess = new Boolean[numQMDistractors];
					for(int b=0; b<qmDistractorSuccess.length; b++) qmDistractorSuccess[b]=false;
					for(int j=0; j<numQMDistractors; j++){
						int maxAttempts_qm = 3;
						int nTries_qm = 0;
						while(nTries_qm < maxAttempts_qm) {
							try {
								setProperties(objs_distractor.get(i).get(j));
								qmDistractorSuccess[j] = objs_distractor.get(i).get(j).genQualitativeMorphedLeafMatchStick(leafToMorphIndx, objs_sample.get(i), qmp);
							} catch (Exception e) {
								e.printStackTrace();
								qmDistractorSuccess[j]=false;
							}
							if(!qmDistractorSuccess[j]) {
								objs_distractor.get(i).set(j, new AllenMatchStick());
							} else {
								break;
							}
							nTries_qm++;
						}
					}
					qmDistractorsSuccess = !Arrays.asList(qmDistractorSuccess).contains(false);


				}
				if(qmDistractorsSuccess){
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



			//GENERATING RAND DISTRACTORS
			System.out.println("Trying to Generate Rand Distractor");
			boolean randDistractorsSuccess = false;
			Boolean[] randDistractorSuccess = new Boolean[numRandDistractors];
			for(int b=0; b<randDistractorSuccess.length; b++) randDistractorSuccess[b]=false;
			for(int j=0; j<numRandDistractors; j++) {
				try {
					setProperties(objs_distractor.get(i).get(j+numQMDistractors));
					objs_distractor.get(i).get(j+numQMDistractors).genMatchStickRand();
					randDistractorSuccess[j] = true;
				} catch(Exception e) {
					e.printStackTrace();
					randDistractorSuccess[j] = false;
				}
				if(!randDistractorSuccess[j]) {
					objs_distractor.get(i).set(j+numQMDistractors, new AllenMatchStick());
				}
			}
			randDistractorsSuccess = !Arrays.asList(randDistractorSuccess).contains(false);

			if(randDistractorsSuccess) {
				tryagain = false;
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

			for(int k=0; k<objs.size(); k++) {
				AllenMStickSpec spec = new AllenMStickSpec();
				spec.setMStickInfo(objs.get(k));
				spec.writeInfo2File(generatorSpecPath + "/" + ids.get(k), true);
			}
			
			//SPECIFYING LOCATION
			int numChoices = numQMDistractors+numRandDistractors+1; //#Distractors + Match
			Coordinates2D sampleCoords = randomWithinRadius(sampleRadiusLowerLim, sampleRadiusUpperLim);
			DistancedDistractorsUtil ddUtil = new DistancedDistractorsUtil(numChoices, choiceRadiusLowerLim, choiceRadiusUpperLim, distractorDistanceLowerLim,  distractorDistanceUpperLim);
			ArrayList<Coordinates2D> distractorsCoords = (ArrayList<Coordinates2D>) ddUtil.getDistractorCoordsAsList();
			Coordinates2D matchCoords = ddUtil.getMatchCoords();

			//SAMPLE
			long taskId = sampleId;
			PngSpec sampleSpec = new PngSpec();
			sampleSpec.setPath(experimentPngPath+"/"+ids.get(0)+".png");
			sampleSpec.setxCenter(sampleCoords.getX());
			sampleSpec.setyCenter(sampleCoords.getY());
			ImageDimensions sampleDimensions = new ImageDimensions(sampleScaleUpperLim, sampleScaleUpperLim);
			sampleSpec.setImageDimensions(sampleDimensions);
			dbUtil.writeStimObjData(sampleId, sampleSpec.toXml(), "sample");

			//
			long[] choiceIds = new long[numChoices];

			//MATCH
			PngSpec matchSpec = new PngSpec();
			matchSpec.setPath(experimentPngPath+"/"+ids.get(1)+".png");
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
				distractorSpec.get(j).setPath(experimentPngPath+"/"+ids.get(j+2)+".png");
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
		double scale = maxImageDimensionDegrees/1.5;
		double minScale = maxImageDimensionDegrees/2.5;
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

	public QualitativeMorphParameterGenerator getQmpGenerator() {
		return qmpGenerator;
	}

	public void setQmpGenerator(QualitativeMorphParameterGenerator qmpGenerator) {
		this.qmpGenerator = qmpGenerator;
	}

	public MetricMorphParameterGenerator getMmpGenerator() {
		return mmpGenerator;
	}

	public void setMmpGenerator(MetricMorphParameterGenerator mmpGenerator) {
		this.mmpGenerator = mmpGenerator;
	}

	public String getGeneratorSpecPath() {
		return generatorSpecPath;
	}

	public void setGeneratorSpecPath(String generatorSpecPath) {
		this.generatorSpecPath = generatorSpecPath;
	}

}
