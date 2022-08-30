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
import org.xper.allen.nafc.vo.NoiseType;
import org.xper.allen.specs.NAFCStimSpecSpec;
import org.xper.allen.specs.PngSpec;
import org.xper.allen.util.AllenDbUtil;
import org.xper.allen.util.AllenXMLUtil;
import org.xper.drawing.Coordinates2D;
import org.xper.exception.VariableNotFoundException;
import org.xper.time.TimeUtil;
import org.xper.utils.RGBColor;

import static org.xper.allen.nafc.blockgen.NAFCCoordinateAssigner.randomCoordsWithinRadii;

/**
 * Generate MSticks, convert to Png. 
 * @author r2_allen
 *
 */
public class MStickPngBlockGen extends AbstractTrialGenerator{
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

	public MStickPngBlockGen() {
	}

	long genId = 1;
	List<Long> ids = new ArrayList<Long>();

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
			Integer[] numQMCategoriesTypes, double[] numQMCategoriesFrequencies) { //
		
		int[] numDistractorsNumTrials = frequencyToNumTrials(numDistractorsFrequencies, numTrials);
		int[] numQMDistractorsNumTrials = frequencyToNumTrials(numQMDistractorsFrequencies, numTrials);
		int[] numQMCategoriesNumTrials = frequencyToNumTrials(numQMCategoriesFrequencies, numTrials);

		
		generate(numDistractorsTypes, numDistractorsNumTrials,
				sampleScaleUpperLim, sampleRadiusLowerLim, sampleRadiusUpperLim, 
				eyeWinSize, choiceRadiusLowerLim, choiceRadiusUpperLim, 
				 distractorDistanceLowerLim,
				distractorDistanceUpperLim,
				distractorScaleUpperLim, numMMCategories, numQMDistractorsTypes, numQMDistractorsNumTrials,
				numQMCategoriesTypes, numQMCategoriesNumTrials);
	}
	
	
	public void generate(Integer[] numDistractors_types, int[] numDistractors_numTrials,
			double sampleScaleUpperLim, double sampleRadiusLowerLim, 
			double sampleRadiusUpperLim, double eyeWinSize, 
			double choiceRadiusLowerLim, double choiceRadiusUpperLim, 
			double distractorDistanceLowerLim, 
			double distractorDistanceUpperLim,
			double distractorScaleUpperLim, double metricMorphMagnitude,
			Integer[] numQMDistractors_types, int[] numQMDistractors_numTrials,
			Integer[] numCategoriesMorphed_types, int[] numCategoriesMorphed_numTrials) { //



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
				int leafToMorphIndx = objs_sample.get(i).getSpecialEndComp().get(0);
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
			pngMaker.createAndSaveBatchOfPNGs(objs, ids, null);

			for(int k=0; k<objs.size(); k++) {
				AllenMStickSpec spec = new AllenMStickSpec();
				spec.setMStickInfo(objs.get(k));
				spec.writeInfo2File(generatorSpecPath + "/" + ids.get(k), true);
			}
			
			//SPECIFYING LOCATION
			int numChoices = numQMDistractors+numRandDistractors+1; //#Distractors + Match
			Coordinates2D sampleCoords = randomCoordsWithinRadii(sampleRadiusLowerLim, sampleRadiusUpperLim);
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
