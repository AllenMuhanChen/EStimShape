package org.xper.allen.nafc.blockgen;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;
import java.util.Random;
import java.util.stream.IntStream;

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
import org.xper.allen.specs.NAFCStimSpecSpec;
import org.xper.allen.specs.NoisyPngSpec;
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
public class NoisyMStickPngRandBlockGen extends NAFCBlockGen{
	@Dependency
	AllenDbUtil dbUtil;
	@Dependency
	TimeUtil globalTimeUtil;
	@Dependency
	AllenXMLUtil xmlUtil;
	@Dependency
	protected
	String generatorPngPath;
	@Dependency
	protected
	String experimentPngPath;
	@Dependency
	protected
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

	public NoisyMStickPngRandBlockGen() {
	}

	long genId = 1;
	List<Long> ids = new ArrayList<Long>();

	/**
	 * Using frequencies
	 * @param numTrials
	 * @param numDistractorsTypes
	 * @param numDistractorsFrequencies
	 * @param sampleScaleUpperLim
	 * @param sampleRadiusLowerLim
	 * @param sampleRadiusUpperLim
	 * @param eyeWinSize
	 * @param choiceRadiusLowerLim
	 * @param choiceRadiusUpperLim
	 * @param distractorDistanceLowerLim
	 * @param distractorDistanceUpperLim
	 * @param distractorScaleUpperLim
	 * @param numMMCategories
	 * @param numQMDistractorsTypes
	 * @param numQMDistractorsFrequencies
	 * @param numQMCategoriesTypes
	 * @param numQMCategoriesFrequencies
	 * @param noiseTypes
	 * @param noiseTypesFrequencies
	 * @param noiseChances
	 * @param noiseChancesFrequencies
	 */
	public void generate(int numTrials,
			Integer[] numDistractorsTypes, double[] numDistractorsFrequencies,
			double sampleScaleUpperLim, double sampleRadiusLowerLim, 
			double sampleRadiusUpperLim, 
			double eyeWinSize, 
			double choiceRadiusLowerLim, double choiceRadiusUpperLim, 
			double distractorDistanceLowerLim, double distractorDistanceUpperLim,
			double distractorScaleUpperLim, 
			int numMMCategories,
			Integer[] numQMDistractorsTypes, double[] numQMDistractorsFrequencies,
			Integer[] numQMCategoriesTypes, double[] numQMCategoriesFrequencies,
			NoiseType[] noiseTypes, double[] noiseTypesFrequencies,
			double[][] noiseChances, double[] noiseChancesFrequencies) { //

		int[] numDistractorsNumTrials = frequencyToNumTrials(numDistractorsFrequencies, numTrials);
		int[] numQMDistractorsNumTrials = frequencyToNumTrials(numQMDistractorsFrequencies, numTrials);
		int[] numQMCategoriesNumTrials = frequencyToNumTrials(numQMCategoriesFrequencies, numTrials);
		int[] noiseTypesNumTrials = frequencyToNumTrials(noiseTypesFrequencies, numTrials);
		int[] noiseChancesNumTrials = frequencyToNumTrials(noiseChancesFrequencies, numTrials);

		generate(numDistractorsTypes, numDistractorsNumTrials,
				sampleScaleUpperLim, sampleRadiusLowerLim, sampleRadiusUpperLim, 
				eyeWinSize, choiceRadiusLowerLim, choiceRadiusUpperLim, 
				distractorDistanceLowerLim,
				distractorDistanceUpperLim,
				distractorScaleUpperLim, numMMCategories, numQMDistractorsTypes, numQMDistractorsNumTrials,
				numQMCategoriesTypes, numQMCategoriesNumTrials,
				noiseTypes, noiseTypesNumTrials,
				noiseChances, noiseChancesNumTrials);
	}



	/**
	 * using numTrials
	 * @param numDistractorsTypes
	 * @param numDistractorsNumTrials
	 * @param sampleScaleUpperLim
	 * @param sampleRadiusLowerLim
	 * @param sampleRadiusUpperLim
	 * @param eyeWinSize
	 * @param choiceRadiusLowerLim
	 * @param choiceRadiusUpperLim
	 * @param distractorDistanceLowerLim
	 * @param distractorDistanceUpperLim
	 * @param distractorScaleUpperLim
	 * @param numMMCategories
	 * @param numQMDistractorsTypes
	 * @param numQMDistractorsNumTrials
	 * @param numQMCategoriesTypes
	 * @param numQMCategoriesNumTrials
	 * @param noiseTypes
	 * @param noiseTypesNumTrials
	 * @param noiseChances
	 * @param noiseChancesNumTrials
	 */
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
		List<NoiseType> noiseTypesTrialList = populateTrials(numTrials, noiseTypes, noiseTypesNumTrials);
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
		List<List<QualitativeMorphParams>> qmps = new LinkedList<>();
		List<MetricMorphParams> mmps = new LinkedList<>();
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
			MetricMorphParams mmp = new MetricMorphParams();
			mmp = mmpGenerator.getMMP(sampleScaleUpperLim, numMMCategories);
			mmps.add(mmp);
			
			qmps.add(new LinkedList<QualitativeMorphParams>());
			for(int qmIndx = 0; qmIndx<numQMDistractors; qmIndx++) {
				qmps.get(i).add(qmpGenerator.getQMP(numQMCategories));
			}

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
				int leafToMorphIndx = -1;
				if(sampleSuccess){
					leafToMorphIndx = objs_sample.get(i).getSpecialEndComp().get(0);
					int maxAttempts_match = 3;
					int nTries_match = 0;
					//int leafToMorphIndx = objs_sample.get(i).chooseRandLeaf(); 
					//boolean maintainTangent = true;
					while(nTries_match<maxAttempts_match) {
						System.out.println("In Match");
						try{
							setProperties(objs_match.get(i));
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
								qmDistractorSuccess[j] = objs_distractor.get(i).get(j).genQualitativeMorphedLeafMatchStick(leafToMorphIndx, objs_sample.get(i), qmps.get(i).get(j));
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

		}
		
		List<AllenMatchStick> objs = new LinkedList<AllenMatchStick>();
		List<AllenMatchStick> objs_noise = new LinkedList<AllenMatchStick>();
		List<List<String>> labels = new LinkedList<>();
		List<List<String>> noiseLabels = new LinkedList<>();
		List<Long> ids = new LinkedList<Long>();
		List<Long> ids_noise = new LinkedList<Long>();
		List<NoiseData> noiseData= new LinkedList<NoiseData>();
		List<Long> sampleIds = new LinkedList<Long>();
		List<Long> matchIds = new LinkedList<Long>();
		List<List<Long>> distractorIds = new LinkedList<>();
		
		for (int i = 0; i < numTrials; i++) {
			int numQMDistractors = numQMDistractorsTrialList.get(i);
			int numRandDistractors = numDistractorsTrialList.get(i)-numQMDistractors;
			//add objs for pngs to draw
			objs.add(objs_sample.get(i)); 
			objs_noise.add(objs_sample.get(i));
			objs.add(objs_match.get(i));
			objs.addAll(objs_distractor.get(i));
			
			//Determine Ids
			long sampleId = globalTimeUtil.currentTimeMicros();
			sampleIds.add(sampleId);
			long matchId = sampleId + 1;
			matchIds.add(matchId);
			List<Long> distractorId = new LinkedList<Long>();
			for (int j=0; j<objs_distractor.get(i).size(); j++){
				distractorId.add(matchId + j + 1);
			}
			distractorIds.add(distractorId);
			
			ids.add(sampleId);
			ids_noise.add(sampleId);
			ids.add(matchId);
			ids.addAll(distractorId);
			
			
			//LABELS
			List<String> sampleLabels = Arrays.asList(new String[] {"sample"});
			labels.add(sampleLabels);
			noiseLabels.add(sampleLabels);
			List<String> matchLabels = Arrays.asList(new String[] {"match"});
			labels.add(matchLabels);
			for(int k=0; k<numQMDistractors; k++) {
				List<String> distractorLabels = Arrays.asList(new String[] {"distractor", "qualitativeMorph"});
				labels.add(distractorLabels);
			}

			for(int k=0; k<numRandDistractors; k++) {
				List<String> distractorLabels = Arrays.asList(new String[] {"distractor", "rand"});
				labels.add(distractorLabels);
			}
			
			//SETTING NOISE DATA
			NoiseType noiseType = noiseTypesTrialList.get(i);
			double[] noiseChance = noiseChancesTrialList.get(i);
			noiseData.add(objs_noise.get(i).setNoiseParameters(noiseType, noiseChance));
		}
		
		
		List<String> stimPaths = pngMaker.createAndSavePNGsfromObjs(objs, ids, labels);
		stimPaths = convertPathsToExperiment(stimPaths);
		List<String> noiseMapPaths = pngMaker.createAndSaveNoiseMapfromObjs(objs_noise, ids_noise, noiseLabels);
		noiseMapPaths = convertPathsToExperiment(noiseMapPaths);
		
		//SAVE SPECS.TXT
		for(int k=0; k<objs.size(); k++) {
			AllenMStickSpec spec = new AllenMStickSpec();
			spec.setMStickInfo(objs.get(k));
			spec.writeInfo2File(getGeneratorSpecPath() + "/" + ids.get(k), true);
			System.out.println("SAVING SPEC " + k + " out of " + objs.size());
		}
		
		int prevIndx=0;
		for (int i = 0; i < numTrials; i++) {
			int tmpIndx=0;
			int numQMDistractors = numQMDistractorsTrialList.get(i);
			int numRandDistractors = numDistractorsTrialList.get(i)-numQMDistractors;
			if(numRandDistractors<0) throw new IllegalArgumentException("There should not be less than 0 randDistractors");
			int numQMCategories = numCategoriesMorphedTrialList.get(i);
			int numChoices = numQMDistractors+numRandDistractors+1; //#Distractors + Match
			int numStimuli = numChoices + 1; //choices + sample
			
			List<String> trialStimPaths = new LinkedList<String>();
			trialStimPaths.add(stimPaths.get(prevIndx+0)); //sample
			tmpIndx++;
			trialStimPaths.add(stimPaths.get(prevIndx+1)); //match
			tmpIndx++;
			for(int j=0; j<numQMDistractors; j++) {
				trialStimPaths.add(stimPaths.get(prevIndx+j+2));
				tmpIndx++;
			}
			for(int j=numQMDistractors; j<numChoices-1; j++) {
				trialStimPaths.add(stimPaths.get(prevIndx+j+2));
				tmpIndx++;
			}
			prevIndx = prevIndx+tmpIndx;
			

			//PREPARING WRITE TO DB SPECIFYING LOCATION
			
			Coordinates2D sampleCoords = randomWithinRadius(sampleRadiusLowerLim, sampleRadiusUpperLim);
			DistancedDistractorsUtil ddUtil = new DistancedDistractorsUtil(numChoices, choiceRadiusLowerLim, choiceRadiusUpperLim, distractorDistanceLowerLim,  distractorDistanceUpperLim);
			ArrayList<Coordinates2D> distractorsCoords = (ArrayList<Coordinates2D>) ddUtil.getDistractorCoordsAsList();
			Coordinates2D matchCoords = ddUtil.getMatchCoords();

			//SAMPLE SPEC
			long taskId = sampleIds.get(i);
			NoisyPngSpec sampleSpec = new NoisyPngSpec();
			//			sampleSpec.setPath(experimentPngPath+"/"+ids.get(0)+".png");
			sampleSpec.setPath(trialStimPaths.get(0));
			sampleSpec.setNoiseMapPath(noiseMapPaths.get(i));
			sampleSpec.setxCenter(sampleCoords.getX());
			sampleSpec.setyCenter(sampleCoords.getY());
			ImageDimensions sampleDimensions = new ImageDimensions(sampleScaleUpperLim, sampleScaleUpperLim);
			sampleSpec.setImageDimensions(sampleDimensions);
			dbUtil.writeStimObjData(sampleIds.get(i), sampleSpec.toXml(), "Sample");

			//
			long[] choiceIds = new long[numChoices];

			//MATCH SPEC
			NoisyPngSpec matchSpec = new NoisyPngSpec();
			//			matchSpec.setPath(experimentPngPath+"/"+ids.get(1)+".png");
			matchSpec.setPath(trialStimPaths.get(1));
			matchSpec.setxCenter(matchCoords.getX());
			matchSpec.setyCenter(matchCoords.getY());
			ImageDimensions matchDimensions = new ImageDimensions(sampleScaleUpperLim, sampleScaleUpperLim);
			matchSpec.setImageDimensions(matchDimensions);
			dbUtil.writeStimObjData(matchIds.get(i), matchSpec.toXml(), "Match");
			choiceIds[0] = matchIds.get(i);

			//DISTRACTORS SPECS
			List<NoisyPngSpec> distractorSpec = new ArrayList<NoisyPngSpec>();
			for(int j=0; j<numQMDistractors; j++){
				distractorSpec.add(j, new NoisyPngSpec());
				//				distractorSpec.get(j).setPath(experimentPngPath+"/"+ids.get(j+2)+".png");
				distractorSpec.get(j).setPath(trialStimPaths.get(j+2));
				distractorSpec.get(j).setxCenter(distractorsCoords.get(j).getX());
				distractorSpec.get(j).setyCenter(distractorsCoords.get(j).getY());
				ImageDimensions distractorDimensions = new ImageDimensions(distractorScaleUpperLim, distractorScaleUpperLim);
				distractorSpec.get(j).setImageDimensions(distractorDimensions);

				dbUtil.writeStimObjData(distractorIds.get(i).get(j), distractorSpec.get(j).toXml(), "QM");
				choiceIds[j+1] = distractorIds.get(i).get(j);
			}
			for(int j=numQMDistractors; j<numChoices-1; j++){
				distractorSpec.add(j, new NoisyPngSpec());
				//				distractorSpec.get(j).setPath(experimentPngPath+"/"+ids.get(j+2)+".png");
				distractorSpec.get(j).setPath(trialStimPaths.get(j+2));
				distractorSpec.get(j).setxCenter(distractorsCoords.get(j).getX());
				distractorSpec.get(j).setyCenter(distractorsCoords.get(j).getY());
				ImageDimensions distractorDimensions = new ImageDimensions(distractorScaleUpperLim, distractorScaleUpperLim);
				distractorSpec.get(j).setImageDimensions(distractorDimensions);
				dbUtil.writeStimObjData(distractorIds.get(i).get(j), distractorSpec.get(j).toXml(), "RAND");
				choiceIds[j+1] = distractorIds.get(i).get(j);
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
			NAFCStimSpecSpec stimSpec = new NAFCStimSpecSpec(targetEyeWinCoords.toArray(new Coordinates2D[0]), targetEyeWinSizeArray, sampleIds.get(i), choiceIds, eStimObjData, rewardPolicy, rewardList);

			//WRITE TRIAL DATA
			NoisyMStickNAFCRandTrialGenData genData = new NoisyMStickNAFCRandTrialGenData(numQMDistractors+numRandDistractors, 
					numQMDistractors, numRandDistractors, numQMCategories, numMMCategories, 
					sampleScaleUpperLim, distractorScaleUpperLim, new double[] {sampleRadiusLowerLim, sampleRadiusUpperLim}, eyeWinSize, 
					new double[] {choiceRadiusLowerLim, choiceRadiusUpperLim}, new double[] {distractorDistanceLowerLim, distractorDistanceUpperLim});


			NoisyMStickNAFCRandTrialData trialData = new NoisyMStickNAFCRandTrialData(genData, noiseData.get(i), qmps.get(i), mmps.get(i));


			dbUtil.writeStimSpec(taskId, stimSpec.toXml(), trialData.toXml());
			dbUtil.writeTaskToDo(taskId, taskId, -1, genId);
			
			System.out.println("Wrote Task " + i + " to DB out of " + numTrials);

		}
		dbUtil.updateReadyGenerationInfo(genId, numTrials);
		System.out.println("Done Generating...");

		return;
	}



	/**
	 * It is imperative that these properties are set before the object is generated/is smoothized.
	 * @param obj
	 */
	protected void setProperties(AllenMatchStick obj) {
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


	public List<String> convertPathsToExperiment(List<String> generatorPaths) {
		LinkedList<String> expPaths = new LinkedList<String>();
		for(int s=0; s<generatorPaths.size(); s++) {
			String newPath = generatorPaths.get(s).replace(getGeneratorPngPath(), getExperimentPngPath());
			expPaths.add(s, newPath);
		}
		return expPaths;
	}
	


	public String convertPathToExperiment(String generatorPath) {

		String newPath = generatorPath.replace(getGeneratorPngPath(), getExperimentPngPath());

		return newPath;
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
