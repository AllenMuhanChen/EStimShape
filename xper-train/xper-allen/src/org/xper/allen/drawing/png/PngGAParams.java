package org.xper.allen.drawing.png;

public final class PngGAParams {
	public static final boolean stereo = false;
	
	public static final int GA_maxNumGens = 10;
	public static final int GA_numNonBlankStimsPerLin = 50;	//40 10 // add additional stimuli that are from library...
	public static final int GA_numStimsPerLin = GA_numNonBlankStimsPerLin + 1;
	public static final int GA_numRepsPerStim = 5; //5			
	public static final int GA_numStimsPerTrial = 4;
	public static final int GA_numLineages = 2;
	public static final int GA_numTasks = (int) Math.ceil(((double)(GA_numStimsPerLin*GA_numRepsPerStim))/((double)(GA_numStimsPerTrial))); //#####! was (int) Math.ceil(GA_numStimsPerLin*GA_numLineages*GA_numRepsPerStim/GA_numStimsPerTrial)
	public static final int numRenderNodes = 12;
	public static final int GA_numFreshStimsPerLin = numRenderNodes;
	public static final int GA_numRandomLibraryStimsPerLin = GA_numNonBlankStimsPerLin-GA_numFreshStimsPerLin;
	
	public static double GA_randgen_prob_objvsenvt = 0.75; 					// probability random stimulus will be alden-containing "Object" (vs "Environment")
	
	public static int GA_morph_numNewStimPerLin = 3; 							// was 5. number of new random stimuli per lineage (10% - 20% of total stimuli)
	public static double GA_morph_prob_stick = 0.7; 							// probability of stick spec morph: new stick or stick morph (vs blender spec morph)
	public static double GA_morph_prob_stick_new = 0.1; 						// probability stick spec morph will produce new stick (vs stick morph)
	
	public static double[] GA_percentDivs = {0.3,0.5,0.7,0.9,1.0}; 			// thresholds on Z-score performance distribution for response binning
//	public static double[] GA_fracPerPercentDiv = {0.1,0.15,0.2,0.2,0.35}; 	// percent of stimuli to morph chosen from each GA_percentDivs bin
	public static double[] GA_fracPerPercentDiv = {0.05,0.05,0.2,0.3,0.4}; 	// percent of stimuli to morph chosen from each GA_percentDivs bin
	
	public static int PH_numObjects_fitnessMethod = 4;
	public static int PH_stability_numMorphs = 5; 							// STABILITY: 	will remain the same unless burial depth selection changes: low pot with all depths (5) + high pot " (5)
	public static int PH_perturbation_numMorphs = 18;							// PERTURBATION:	4 rotations, 2 leans, 2 depths
	public static int[] PH_bulbousness_morphs = {1,3,4,5,6};					// MASS: 		shape morph types applied to selected limb in mass posthoc
	public static int PH_animacy_numFrames = 30;
	public static int PH_animacy_numMaterials = 1;							// ANIMACY: 		how many of squish/stiff materials should be used
	public static int targetedColoration = 0; 								// ANIMACY: 		extent to which squish/stiff materials are represented on the object
	public static int PH_max_animacy_animations = 3; 							// ANIMACY: 		maximum of three limb animations per object
	public static int PH_numResponders_highLow = 3; 							// GENERAL: 		method 1: number of highest-/lowest-response stimuli selected for post-hoc
	public static double[] PH_percentDivs = {0.3,0.8,1.0}; 					// GENERAL: 		method 2: thresholds on Z-score performance distribution for low-, medium-, high-response stimulus selection
	public static int PH_distance_numDistances = 6;
	
	// PngRandomGeneration
	public static final String basePath = "/home/alexandriya/blendRend/ProgressionClasses/"; 
	
	// ImageStack
	public static final String resourcePath = "/home/alexandriya/catch_cluster_images/"; 
	
	// PngExptScene
	public static final String fixationImageStr = "/home/alexandriya/catch_cluster_images/BLANK/BLANK_FIX"; //"/Users/ecpc31/Dropbox/Blender/catch_cluster_images/Rendered//BLANK/BLANK_FIX";
	public static final String blankImageStr = "/home/alexandriya/catch_cluster_images/BLANK/BLANK"; //"/Users/ecpc31/Dropbox/Blender/catch_cluster_images/Rendered/BLANK/BLANK";
	
	// BlenderRunnable
	public static final String appPath = "/home/alexandriya/blender/blender"; //"/Applications/blender-279/Blender.app/Contents/MacOS/blender";
	public static final String blendFile = "/home/alexandriya/blendRend/ProgressionClasses/frameRate.blend"; //"/Users/ecpc31/Dropbox/Blender/ProgressionClasses/frameRate.blend";

}
