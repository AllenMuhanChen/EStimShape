package org.xper.allen.nafc.blockgen.psychometric;

import java.io.File;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.xper.Dependency;
import org.xper.allen.drawing.composition.AllenMAxisArc;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.AllenTubeComp;
import org.xper.allen.drawing.composition.qualitativemorphs.PsychometricQualitativeMorphParameterGenerator;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphParams;
import org.xper.allen.drawing.png.ImageDimensions;
import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.blockgen.NoiseChances;
import org.xper.allen.nafc.blockgen.SampleDistance;
import org.xper.allen.nafc.blockgen.Trial;
import org.xper.allen.nafc.experiment.RewardPolicy;
import org.xper.allen.nafc.vo.MStickStimObjData;
import org.xper.allen.nafc.vo.NoiseParameters;
import org.xper.allen.nafc.vo.NoiseType;
import org.xper.allen.specs.NAFCStimSpecSpec;
import org.xper.allen.specs.NoisyPngSpec;
import org.xper.drawing.Coordinates2D;
import org.xper.exception.VariableNotFoundException;

public class PsychometricBlockGen extends AbstractPsychometricTrialGenerator{
	
	@Dependency
	PsychometricQualitativeMorphParameterGenerator psychometricQmpGenerator;
	
	Long genId;
	
	

	public void generateImageSet(int numPerSet, double size, double percentChangePosition, int numRand) {	
		if(numRand>numPerSet) {
			throw new IllegalArgumentException("numRand should not be greater than numPerSet");
		}

		//Preallocation & Set-up
		List<StimType> stimTypes = new LinkedList<>();
		boolean tryagain = true;
		int nTries = 0;
		AllenMatchStick objs_base = new AllenMatchStick();
		List<AllenMatchStick> objs = new ArrayList<>();
		for(int i=0; i<numPerSet; i++) {
			objs.add(new AllenMatchStick());

			if(i==0) {
				stimTypes.add(StimType.BASE);
			} 
			else if (i>0 && i<numPerSet-numRand) {
				stimTypes.add(StimType.QM);
			} else {
				stimTypes.add(StimType.RAND);
			}
		}

		int numQMMorphs = numPerSet-1;
		List<QualitativeMorphParams> qmps = new LinkedList<>();
		qmps = psychometricQmpGenerator.getQMP(numPerSet-1-numRand, percentChangePosition);

		//VETTING AND CHOOSING LEAF
		while (tryagain){
			boolean firstObjSuccess = false;
			Boolean[] restObjSuccess = new Boolean[numPerSet-1];
			for(int b=0; b<restObjSuccess.length; b++) restObjSuccess[b]=false;
			boolean restOfObjsSuccess = false;

			setProperties(objs_base);

			//LEAF
			int randomLeaf=-1;
			{

				int nTries_leaf=0;

				while(true) {
					System.out.println("In Leaf: Attempt " + (nTries_leaf+1));
					objs_base.genMatchStickRand();
					randomLeaf = objs_base.chooseRandLeaf();
					boolean leafSuccess = objs_base.vetLeaf(randomLeaf);
					if(!leafSuccess) {
						objs_base = new AllenMatchStick();
					} else {
						break;
					}
					nTries_leaf++;
				}
			}

			int maxAttemptsPerObj = 3;


			//FIRST OBJ
			int nTries_obj = 0;
			while(nTries_obj<maxAttemptsPerObj) {
				//				System.out.println("In Obj " + 0 + ": attempt " + nTries_obj + " out of " + maxAttemptsPerObj);
				setProperties(objs.get(0));
				firstObjSuccess = objs.get(0).genMatchStickFromLeaf(randomLeaf, objs_base);
				if(!firstObjSuccess){
					objs.set(0, new AllenMatchStick());
				}
				else {
					break;
				}
				nTries_obj++;
			}

			//REST OF THE OBJS
			if(firstObjSuccess) {
				int leafToMorphIndx = objs.get(0).getSpecialEndComp().get(0);
				for (int i=1; i<numPerSet; i++) {
					nTries_obj = 0;
					while(nTries_obj<maxAttemptsPerObj) {
						//						System.out.println("In Obj " + i + ": attempt " + nTries_obj + " out of " + maxAttemptsPerObj);
						try {
							setProperties(objs.get(i));
							if(stimTypes.get(i)==StimType.QM)
								restObjSuccess[i-1] = objs.get(i).genQualitativeMorphedLeafMatchStick(leafToMorphIndx, objs.get(0), qmps.get(i-1));
							else {
								try {
								objs.get(i).genMatchStickRand();
								restObjSuccess[i-1] = true;
								} catch (Exception e) {
									restObjSuccess[i-1] = false;
								}
							}
						} catch (Exception e) {
							e.printStackTrace();
							restObjSuccess[i-1] = false;
						}
						if(!restObjSuccess[i-1]){
							objs.set(i, new AllenMatchStick());
						}
						else {
							break;
						}
						nTries_obj++;
					}

				}
				restOfObjsSuccess = !Arrays.asList(restObjSuccess).contains(false);
			}
			if(restOfObjsSuccess) {
				tryagain = false;
				System.out.println("SUCCESS!");
			} else {
				tryagain = true;
				nTries++;
				System.out.println("TRYING AGAIN: " + nTries + " tries.");
			}
		}

//		//DEBUG
//		for (AllenMatchStick obj : objs) {
//			int specialComp = obj.getSpecialEndComp();
//			AllenTubeComp specialCompTube = obj.getComp()[specialComp];
//			AllenMAxisArc specialCompMAxis = specialCompTube.getmAxisInfo();
//			int rotCenter = specialCompMAxis.getTransRotHis_rotCenter();
//			//			System.out.println("AC0000: " + specialCompMAxis.getmTangent()[rotCenter]);
//		}

		//DRAWING AND SAVING
		List<List<String>> labels = new LinkedList<List<String>>();
		List<Long> ids = new LinkedList<Long>();

		long setId = globalTimeUtil.currentTimeMicros();
		for(int i=0; i<numPerSet; i++) {
			List<String> label = new ArrayList<String>();
			label.add(Integer.toString(i));
			labels.add(label);
			ids.add(setId);
		}

		List<String> stimPaths = pngMaker.createAndSaveBatchOfPNGs(objs, ids, labels, null);

		//SAVE SPECS.TXT
		for(int k=0; k<objs.size(); k++) {
			AllenMStickSpec spec = new AllenMStickSpec();
			spec.setMStickInfo(objs.get(k));
			spec.writeInfo2File(getGeneratorSpecPath() +"/" + ids.get(k) + "_" + labels.get(k).get(0), true);
		}
	}


	public void generate(
			int numPsychometricTrialsPerImage, 
			int numRandTrials, 
			NoiseChances noiseChances, 
			SampleDistance sampleDistance,
			Lims choiceDistance, 
			double sampleScale, double eyeWinSize){

		//Start a Drawing Window
		pngMaker.createDrawerWindow();
		
		//Noise chance per each trial per set. 
		List<double[]> noiseChanceTrialList = populateTrials(numPsychometricTrialsPerImage,  noiseChances.noiseChances, noiseChances.noiseChancesProportions);

		int numSets;
		int numStimPerSet;
		//Getting all files in path
		File folder = new File(generatorPngPath);
		File[] fileArray = folder.listFiles();
		List<File> pngs = new ArrayList<>();
		List<String> generatorPngs = new ArrayList<>();

		//Making sure all the files are png
		for(File file:fileArray) {
			if(file.toString().contains(".png")) {
				pngs.add(file);
			}
		}

		//Load filenames
		List<String> filenames = new ArrayList<String>();
		for (File png:pngs) {
			filenames.add(png.getName());
		}
		//For each png, finds the set number and stim number
		List<Long> setIds = new ArrayList<Long>();
		List<Integer> stimIds = new ArrayList<Integer>();
		for(String filename: filenames) {
			Pattern p = Pattern.compile("([0-9]{16})_(\\d)");
			Matcher m = p.matcher(filename);

			if(m.find()) {
				setIds.add(Long.parseLong(m.group(1)));
				stimIds.add(Integer.parseInt(m.group(2)));
			} else {
				throw new IllegalStateException("Can't find any pngs with name pattern regex ([0-9]{16})_(\\d)");
			}
		}

		//Removing non-distinct setIds and stimNums
		removeNonDistinct(setIds);
		removeNonDistinct(stimIds);

		numSets = setIds.size();
		numStimPerSet = stimIds.size();

		//Generate Trials - Assign samples, matches (identical), and distractors
		//assign Ids, setIds, stimIds, Png Paths, Noise Data/Path for sample
		List<Trial> trials = new LinkedList<>();
		//assigning the samples in a balanced way. (# of times a specific stimulus is the sample is identical for e/a stimulus)
		for(long setId:setIds) {
			for(int stimId:stimIds) {
				for(int i=0;i<numPsychometricTrialsPerImage;i++) {
					int numPsychometricDistractors = stimIds.size()-1;
					
					
					PsychometricTrial trial = new PsychometricTrial(
						this,
						numDistractors,
						psychometricIds,
						noiseChance,
						trialParameters);
					
					PsychometricTrial trial = new PsychometricTrial(this,  numPsychometricDistractors, numRandTrials);
					NoisyTrialParameters trialGenData
					= new NoisyTrialParameters(sampleDistance.getSampleDistanceLowerLim(), sampleDistance.getSampleDistanceLowerLim(), choiceDistance.getLowerLim(), choiceDistance.getUpperLim(), sampleScale, eyeWinSize);
					trial.prepareWrite(setId, stimId, stimIds, null);

					trials.add(trial);
				}
			}
		}

		//SHUFFLING
		Collections.shuffle(trials);


		//POPULATING DATABASES
		try {
			/**
			 * Gen ID is important for xper to be able to load new tasks on the fly. It will only do so if the generation Id is upticked. 
			 */
			genId = dbUtil.readReadyGenerationInfo().getGenId() + 1;
		} catch (VariableNotFoundException e) {
			dbUtil.writeReadyGenerationInfo(genId, 0);
		}
		for (Trial trial:trials) {
			
			Long taskId = trial.write();
			dbUtil.writeTaskToDo(taskId, taskId, -1, genId);
		}
		dbUtil.updateReadyGenerationInfo(genId, trials.size());
		System.out.println("Done Generating...");
		pngMaker.close();
		return;
	}

	private enum StimType{
		QM, RAND, BASE;
	}

	public static void removeNonDistinct(List<? extends Comparable<?>> list)
	{
		int n = list.size();
		// First sort the array so that all
		// occurrences become consecutive
		list.sort(null);

		List<Integer> removeList = new ArrayList<Integer>();
		// Traverse the sorted array
		for (int i = 0; i < n; i++)
		{

			// Move the index ahead while
			// there are duplicates
			while (i < n - 1 &&
					list.get(i).equals(list.get(i+1)))
			{
				removeList.add(i+1);
				i++;
			}

		}
	
		//Remove in reverse order to avoid indcs to remove changing every removal. 
		//We can't copy a generic List easily so we have to do it this way. 
		Collections.reverse(removeList);
		for(int removeIndx : removeList) {
			list.remove(removeIndx);
		}
	
	}


	public PsychometricQualitativeMorphParameterGenerator getPsychometricQmpGenerator() {
		return psychometricQmpGenerator;
	}

	public void setPsychometricQmpGenerator(PsychometricQualitativeMorphParameterGenerator psychometricQmpGenerator) {
		this.psychometricQmpGenerator = psychometricQmpGenerator;
	}

	public String getGeneratorSpecPath() {
		return generatorSpecPath;
	}

	public void setGeneratorSpecPath(String generatorSpecPath) {
		this.generatorSpecPath = generatorSpecPath;
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