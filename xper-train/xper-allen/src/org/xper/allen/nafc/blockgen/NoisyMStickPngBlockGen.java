package org.xper.allen.nafc.blockgen;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;
import java.util.Random;
import java.util.concurrent.ThreadLocalRandom;
import java.util.stream.DoubleStream;
import java.util.stream.IntStream;

import javax.vecmath.Tuple2d;

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
import org.xper.allen.nafc.vo.NoiseData;
import org.xper.allen.nafc.vo.NoiseType;
import org.xper.allen.nafc.vo.NoisyMStickNAFCTrialData;
import org.xper.allen.nafc.vo.NoisyMStickNAFCTrialGenData;
import org.xper.allen.specs.NAFCStimSpecSpec;
import org.xper.allen.specs.NoisyPngSpec;
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
public class NoisyMStickPngBlockGen{
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
	 *  Distractors: completely random match sticks or QM match sticks
	 */	

	public NoisyMStickPngBlockGen() {
	}

	long genId = 1;
	List<Long> ids = new ArrayList<Long>();

	public void generate(int[] numDistractors_types, int[] numDistractors_numTrials,
			double sampleScaleUpperLim, double sampleRadiusLowerLim, 
			double sampleRadiusUpperLim, double eyeWinSize, 
			double choiceRadiusLowerLim, double choiceRadiusUpperLim, 
			double distractorDistanceLowerLim, 
			double distractorDistanceUpperLim,
			double distractorScaleUpperLim, int numMMCategories,
			int[] numQMDistractorsTypes, double[] numQMDistractorsFrequencies,
			Integer[] numQMCategoriesTypes, double[] numQMCategoriesFrequencies,
			NoiseType[] noiseTypes, double[] noiseTypesFrequencies,
			double[][] noiseChances, double[] noiseChancesFrequencies) { //
		
		//TODO: calculate numTrials here and then call generate with numTrials.
		//TODO: add logic for frequencies when there some no QM and no Noise?
	}
	
	public void generate(Integer[] numDistractorsTypes, int[] numDistractorsNumTrials,
			double sampleScaleUpperLim, double sampleRadiusLowerLim, 
			double sampleRadiusUpperLim, double eyeWinSize, 
			double choiceRadiusLowerLim, double choiceRadiusUpperLim, 
			double distractorDistanceLowerLim, double distractorDistanceUpperLim,
			double distractorScaleUpperLim, 
			int numMMCategories,
			Integer[] numQMDistractorsTypes, int[] numQMDistractorsNumTrials,
			Integer[] numQMCategoriesTypes, int[] numQMCategoriesNumTrials,
			NoiseType[] noiseTypes, int[] noiseTypesNumTrials,
			double[][] noiseChances, int[] noiseChancesNumTrials) { //



		//INTERMIXING TYPES OF TRIALS
		//Distractor Num
		int numTrials = IntStream.of(numDistractorsNumTrials).sum(); //Sum all elements of trialNums
		List<Integer> numDistractorsTrialList = populateTrials(numTrials, numDistractorsTypes, numDistractorsNumTrials);
		Collections.shuffle(numDistractorsTrialList);

		//Number of QM Distractors
		List<Integer> numQMDistractorsTrialList = populateTrials(numTrials, numQMDistractorsTypes, numQMDistractorsNumTrials);
		Collections.shuffle(numQMDistractorsTrialList);

		//Number of Categories Morphed in QM
		List<Integer> numCategoriesMorphedTrialList = populateTrials(numTrials, numQMCategoriesTypes, numQMCategoriesNumTrials);
		Collections.shuffle(numCategoriesMorphedTrialList);

		//NoiseTypes
		List<NoiseType> noiseTypesTrialList = populateTrials(numTrials, noiseTypes, noiseChancesNumTrials);
		Collections.shuffle(noiseTypesTrialList);
		
		//NoiseChances
		List<double[]> noiseChancesTrialList = populateTrials(numTrials, noiseChances, noiseChancesNumTrials);
		Collections.shuffle(noiseChancesTrialList);
		
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
			int numQMCategories = numCategoriesMorphedTrialList.get(i);
			NoiseType noiseType = noiseTypesTrialList.get(i);
			double[] noiseChance = noiseChancesTrialList.get(i);
			
			
			//GENERATE BASE (leaf to morph + other limbs), SAMPLE, AND MATCH WITHIN LOOP TO MAKE SURE IF 
			//GENERATE MATCH/SAMPLE FAILS, WE START OVER STARTING AT BASE
			boolean tryagain = true;
			int nTries = 0;


			//SETTING MORPHS - we never want to change our morph because of a fail. Otherwise probability distribution of morph types will be skewed. 
			QualitativeMorphParams qmp = qmpGenerator.getQMP(numQMCategories);
			MetricMorphParams mmp = mmpGenerator.getMMP(sampleScaleUpperLim, numMMCategories);
			
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
				
				//DISTRACTORS: QUALITATIVE MORPHS
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
			List<AllenMatchStick> objs_noise = new LinkedList<AllenMatchStick>();
			List<List<String>> labels = new LinkedList<>();
			List<List<String>> noiseLabels = new LinkedList<>();
			//SAMPLE
			objs.add(objs_sample.get(i)); 
			objs_noise.add(objs_sample.get(i));
			List<String> sampleLabels = Arrays.asList(new String[] {"sample"});
			labels.add(sampleLabels);
			noiseLabels.add(sampleLabels);
			//MATCH
			objs.add(objs_match.get(i));
			List<String> matchLabels = Arrays.asList(new String[] {"match"});
			labels.add(matchLabels);
			//DISTRACTORS
			objs.addAll(objs_distractor.get(i));
			for(int k=0; k<numQMDistractors; k++) {
				List<String> distractorLabels = Arrays.asList(new String[] {"distractor", "qualitativeMorph"});
				labels.add(distractorLabels);
			}
			for(int k=0; k<numRandDistractors; k++) {
				List<String> distractorLabels = Arrays.asList(new String[] {"distractor", "rand"});
				labels.add(distractorLabels);
			}
			
			List<Long> ids = new LinkedList<Long>();
			List<Long> ids_noise = new LinkedList<Long>();
			ids.add(sampleId);
			ids_noise.add(sampleId);
			ids.add(matchId);
			ids.addAll(distractorIds);
			List<String> stimPaths = pngMaker.createAndSavePNGsfromObjs(objs, ids, labels);
			
			//NOISE MAP
			NoiseData noiseData = objs_sample.get(i).setNoiseParameters(noiseType, noiseChance);
			List<String> noiseMapPaths = new ArrayList<String>();
			noiseMapPaths.add("");
			if(noiseType!=NoiseType.NONE) {
				noiseMapPaths = pngMaker.createAndSaveNoiseMapfromObjs(objs_noise, ids_noise, noiseLabels);
			} 

			//SAVE SPECS.TXT
			for(int k=0; k<objs.size(); k++) {
				AllenMStickSpec spec = new AllenMStickSpec();
				spec.setMStickInfo(objs.get(k));
				spec.writeInfo2File(generatorSpecPath + "/" + ids.get(k), true);
			}
			
			//PREPARING WRITE TO DB SPECIFYING LOCATION
			int numChoices = numQMDistractors+numRandDistractors+1; //#Distractors + Match
			Coordinates2D sampleCoords = randomWithinRadius(sampleRadiusLowerLim, sampleRadiusUpperLim);
			DistancedDistractorsUtil ddUtil = new DistancedDistractorsUtil(numChoices, choiceRadiusLowerLim, choiceRadiusUpperLim, distractorDistanceLowerLim,  distractorDistanceUpperLim);
			ArrayList<Coordinates2D> distractorsCoords = (ArrayList<Coordinates2D>) ddUtil.getDistractorCoordsAsList();
			Coordinates2D matchCoords = ddUtil.getMatchCoords();

			//SAMPLE SPEC
			long taskId = sampleId;
			NoisyPngSpec sampleSpec = new NoisyPngSpec();
//			sampleSpec.setPath(experimentPngPath+"/"+ids.get(0)+".png");
			sampleSpec.setPath(stimPaths.get(0));
			sampleSpec.setNoiseMapPath(noiseMapPaths.get(0));
			sampleSpec.setxCenter(sampleCoords.getX());
			sampleSpec.setyCenter(sampleCoords.getY());
			ImageDimensions sampleDimensions = new ImageDimensions(sampleScaleUpperLim, sampleScaleUpperLim);
			sampleSpec.setImageDimensions(sampleDimensions);
			dbUtil.writeStimObjData(sampleId, sampleSpec.toXml(), "sample");

			//
			long[] choiceIds = new long[numChoices];

			//MATCH SPEC
			NoisyPngSpec matchSpec = new NoisyPngSpec();
//			matchSpec.setPath(experimentPngPath+"/"+ids.get(1)+".png");
			matchSpec.setPath(stimPaths.get(1));
			matchSpec.setxCenter(matchCoords.getX());
			matchSpec.setyCenter(matchCoords.getY());
			ImageDimensions matchDimensions = new ImageDimensions(sampleScaleUpperLim, sampleScaleUpperLim);
			matchSpec.setImageDimensions(matchDimensions);
			dbUtil.writeStimObjData(matchId, matchSpec.toXml(), "Match");
			choiceIds[0] = matchId;

			//DISTRACTORS SPECS
			List<NoisyPngSpec> distractorSpec = new ArrayList<NoisyPngSpec>();
			for(int j=0; j<numChoices-1; j++){
				distractorSpec.add(j, new NoisyPngSpec());
//				distractorSpec.get(j).setPath(experimentPngPath+"/"+ids.get(j+2)+".png");
				distractorSpec.get(j).setPath(stimPaths.get(j+2));
				distractorSpec.get(j).setxCenter(distractorsCoords.get(j).getX());
				distractorSpec.get(j).setyCenter(distractorsCoords.get(j).getY());
				ImageDimensions distractorDimensions = new ImageDimensions(distractorScaleUpperLim, distractorScaleUpperLim);
				distractorSpec.get(j).setImageDimensions(distractorDimensions);
				dbUtil.writeStimObjData(distractorIds.get(j), distractorSpec.get(j).toXml(), "Distractor");
				choiceIds[j+1] = distractorIds.get(j);
			}

			//PREPARING WRITING STIM-SPEC TO DB
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

			//WRITE STIM-SPEC
			NAFCStimSpecSpec stimSpec = new NAFCStimSpecSpec(targetEyeWinCoords.toArray(new Coordinates2D[0]), targetEyeWinSizeArray, sampleId, choiceIds, eStimObjData, rewardPolicy, rewardList);

			//WRITE TRIAL DATA
			NoisyMStickNAFCTrialGenData genData = new NoisyMStickNAFCTrialGenData(numQMDistractors+numRandDistractors, 
					numQMDistractors, numRandDistractors, numQMCategories, numMMCategories, 
					sampleScaleUpperLim, distractorScaleUpperLim, new double[] {sampleRadiusLowerLim, sampleRadiusUpperLim}, eyeWinSize, 
					new double[] {choiceRadiusLowerLim, choiceRadiusUpperLim}, new double[] {distractorDistanceLowerLim, distractorDistanceUpperLim});
			
		
			NoisyMStickNAFCTrialData trialData = new NoisyMStickNAFCTrialData(genData, noiseData);
			
	
			dbUtil.writeStimSpec(taskId, stimSpec.toXml(), trialData.toXml());
			dbUtil.writeTaskToDo(taskId, taskId, -1, genId);


		}
		dbUtil.updateReadyGenerationInfo(genId, numTrials);
		System.out.println("Done Generating...");

		return;
	}

	/**
	 * generic method for returning a list of trials<K> 
	 * @param <K>
	 * @param numTrials: totla number of trials in block being generated. Used to double check input is correct
	 * @param types: array of types <K>
	 * @param typesNumTrials: number of trials for each type
	 * @return
	 */
	private <K> List<K> populateTrials(int numTrials, K[] types, int[] typesNumTrials) {
		if(IntStream.of(typesNumTrials).sum()!= numTrials) {
			throw new IllegalArgumentException("Total typesNumTrials should equal total numTrials");
		}
		List<K> trialList = new LinkedList<>();
		int numTypes = types.length;
		for(int i=0; i<numTypes; i++) {
			for (int j=0; j<typesNumTrials[i]; j++) {
				trialList.add(types[i]);
			}
		}
		return trialList;
	}


	private <K> List<K> populateTrials(int numTrials, K[] types, double[] typesFrequency) {
		if(DoubleStream.of(typesFrequency).sum()!= 1.0) {
			throw new IllegalArgumentException("Total Frequencies should add to 1");
		}
		int[] typesNumTrials = new int[types.length];
		for(int i=0; i<types.length; i++) {
			typesNumTrials[i] = (int) Math.round(typesFrequency[i]* (double) numTrials);
		}
		if(IntStream.of(typesNumTrials).sum()!= numTrials) {
			throw new IllegalArgumentException("Total number of trials rounded from frequencies does not equal correct total num of trials");
		}
		
		List<K> trialList = new LinkedList<>();
		int numTypes = types.length;
		for(int i=0; i<numTypes; i++) {
			for (int j=0; j<typesNumTrials[i]; j++) {
				trialList.add(types[i]);
			}
		}
		return trialList;
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