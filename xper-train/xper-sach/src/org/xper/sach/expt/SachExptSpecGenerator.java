package org.xper.sach.expt; 

import java.util.List;
import java.util.ArrayList;
//import java.io.BufferedWriter;
//import java.io.File;
//import java.io.FileWriter;
//import java.io.IOException;

import org.xper.Dependency;
//import org.xper.drawing.Coordinates2D;
import org.xper.drawing.renderer.AbstractRenderer;
//import org.xper.sach.analysis.SachStimDataEntry;
//import org.xper.sach.drawing.screenobj.DiskObject;
//import org.xper.sach.drawing.stimuli.BsplineObject;
//import org.xper.sach.drawing.stimuli.BsplineObjectSpec;
import org.xper.sach.expt.generate.SachRandomGeneration.TrialType;
import org.xper.sach.expt.generate.SachStimSpecGenerator;
import org.xper.sach.util.SachDbUtil;
//import org.xper.sach.util.SachMathUtil;
import org.xper.time.TimeUtil;

//import com.jmatio.io.MatFileReader;
//import com.jmatio.types.MLDouble;

public class SachExptSpecGenerator implements SachStimSpecGenerator {	// ugh, just remove SachStimSpecGenerator!

	@Dependency
	SachDbUtil dbUtil;
	@Dependency
	TimeUtil globalTimeUtil;
	@Dependency
	AbstractRenderer renderer;
	
	
//	// ========================== MATLAB FILE I/O STUFF ==========================
//
//	static String currentExptInfo = "/Users/Ramanujan/Dropbox/Documents/Hopkins/NHP2PV4/projectEphysGA/";
//	static ArrayList<String> fileNames = new ArrayList<String>();
//	
//	// ============================================================================
//	
	
	// variables
	static long rewardAmount = 50;
	static double targetEyeWindowSize = 3; // make smaller
	double morphLineLimit = 0;	// from 0 to 1: 0 is no morphing, 1 is full morphing // TODO: finish this
	
	static public enum StimType { BEH_MedialAxis, BEH_Curvature, BEH, GA, BLANK, NA, GA3D};						// stimulus types
	static public enum BehavioralClass { SAMPLE, MATCH, NON_MATCH, NA };										// behavioral class of stimuli	
//	static public enum BehavStimCats { SEVEN_h, Y_h, downL_downT, I_downT, SEVEN_t, Y_t, downL_J, I_J }; 	// behavioral stimulus categories

	TrialType trialType;	// set via SachRandomGeneration
	long taskId;		
	
	
//	// not currently used, remove? adapt?
//	public SachExptSpec generate() {
//					
////		return generateBehavTask_old();		// this will be performed X number of times -- this may change so that it's dependent on performance
//
//	}
	
	
	// ---------------------------------
	// ---- Beh stimulus generation ----
	// ---------------------------------
		
	// ----- old versions -------
//	private SachExptSpec generateBehavTask_old() {
//		
//		// TRIAL SETUP 
//		SachExptSpec g = new SachExptSpec(); 	// spec for each trial
//		int numObjects = 2;						// number of objects displayed  -- current behavioral task: only 2 objects displayed, sample and match/non-match
//		int targetIndex = -1;					// default: no target
//		int[] allCats = null;
//		int[] matchCats = null;
//		
//		// MATCH/NON-MATCH PROPORTIONS 
//		double percMatches = 0.5;
//		targetIndex = SachMathUtil.randBoolean(percMatches) ? 0 : -1;
//
//		// WHICH CATEGORIES OF STIM TO USE? -- 0 to 7 for each stimulus type -- eventually, after training, allCats and matchCats will both be {0,...,7}
//		allCats = new int[]{0,1,2,3,4,5,6,7};			// these are all categories used (samples and distractors)
//		matchCats = new int[]{0,1,2,3,4,5,6,7};			// these are the categories that will be matched
//		
//		// WHICH TYPE OF STIM TO USE?	
//		StimType type = StimType.BEH_MedialAxis;					// only using medial-axis defined stimuli for now
//		
//		// CREATE FIRST STIMULUS (SAMPLE)
//		BsplineObjectSpec s;
//
//		if (targetIndex >= 0) {											// if it's a match trial, use a match category
//			s = generateBehavStim_old(type,matchCats,BehavioralClass.SAMPLE);
//		} else { 														// otherwise, use any category
//			s = generateBehavStim_old(type,allCats,BehavioralClass.SAMPLE);		
//		}
////		g.addObjectSpec(new BsplineObjectSpec(s));
////		g.addStimObjId(s.getStimObjId());
//		
//		// LOOP -- create match and/or non-match stimuli
//			// first remove the sample category from the categories array so that the non-matches/distractors don't use the sample category
////		int sampleCatUsed = s.getCategory();
////		int[] nonMatchCats = SachMathUtil.removeElement(allCats, sampleCatUsed);
//	
//		for (int i = 0; i < numObjects-1; i ++) {
//			if (i == targetIndex) {								// create match
////				s = generateBehavStim_old(type,new int[]{sampleCatUsed},BehavioralClass.MATCH);
////				g.addObjectSpec(new BsplineObjectSpec(s));
////				g.addStimObjId(s.getStimObjId());
//			} else {											// create non-match
////				s = generateBehavStim_old(type,nonMatchCats,BehavioralClass.NON_MATCH);
////				g.addObjectSpec(new BsplineObjectSpec(s));
////				g.addStimObjId(s.getStimObjId());
//			}
//		}
//		
//		// TRIAL SPECS
//			// for setting the target position to the 'disk' saccadic response spot
//		double pos_x = 0, pos_y = 0;								// default target position
//		if (targetIndex != -1) {									// map target position to the response spot, if no target then just reward fixation
//			pos_x = renderer.mm2deg(DiskObject.getTx());			// set target position to the position of the response disk in deg
//			pos_y = renderer.mm2deg(DiskObject.getTy());	
//		}
//		
////		g.setTargetPosition(new Coordinates2D(pos_x, pos_y));		// (in degrees)
////		g.setTargetEyeWinSize(targetEyeWindowSize);					// use this to change accuracy tolerance (in degrees)
//		//g.setReward((long)(Math.random() * 100 + 100));			// randomize reward size
//		g.setReward(rewardAmount);											// fixed reward size
////		g.setTargetIndex(targetIndex);								// targetIndex indicates which object is the target, if no target then it is -1 and fixation at end of trial is rewarded
//		g.setTrialType(TrialType.BEH.toString());					// shows whether trial is Behavioral or GA
//		
//		return g;	
//	}
	
//	private BsplineObjectSpec generateBehavStim_old(StimType type, int[] categories, BehavioralClass behavClass) {
//		// choose/generate stimulus based on type and categories
//				
//		// STIMULUS CATEGORY -- randomly choose among categories
//		int category = categories[SachMathUtil.randRange(categories.length-1,0)];
//		
//		// STIMULUS SETUP
//		BsplineObjectSpec s = new BsplineObjectSpec();
//		SachStimDataEntry d = new SachStimDataEntry();
//		
//		double xCntr = 0;											// defaults
//		double yCntr = 0;										
//		float size = 4;										
//		
//		xCntr += Math.random() * 10 - 5;							// for randomly jittering the position of stimuli
//		yCntr += Math.random() * 10 - 5;
//		
//		// GENERATE STIM	
//		long stimObjId = globalTimeUtil.currentTimeMicros();
//		
//		// -- set spec values 		
//		s.setStimObjId(stimObjId);
//		s.setStimType(type.toString());
//		s.setBehavioralClass(behavClass.toString());
//		s.setCategory(category);
//		s.setXCenter(xCntr);
//		s.setYCenter(yCntr);
//		s.setSize(size);
//		s.setAnimation(false);
//		s.setDoRandom(false);			// randomly change the lengths (and/or widths) of behavioral simuli
//		s.setDoMorph(false);			// randomly choose object parameters from morph line TODO: remove this and just control w morphLim?
//		s.setMorphLim(morphLineLimit);	// current limit set for morph line 		
//		
//			// want to re-create object spec after running it through the object (BsplineObject), (this saves the limbs info with the spec):
//		BsplineObject obj = new BsplineObject();
//		obj.setSpec(s.toXml());
//		BsplineObjectSpec ss = obj.getSpec();
//		
//		// -- set data values
//		d.setStimObjId(stimObjId);
//		d.setTrialType(TrialType.BEH.toString());
//		
//		// create stimObjId and add it to this and SachStimDataEntry, then write them to the DB
//		dbUtil.writeStimObjData(stimObjId, ss.toXml(), d.toXml());
//		
//		
//		// *** -- for now I am just creating a brand new stimulus each time this is runModeRun (even if the same stimulus is created again)
//		//	  I can sort by category later for analysis (also by morphLim)
//		
//		
//		// TODO: when morph lines are spec'ed out in BsplineObjectSpec, need to keep track of morph line limits for each category
//		//       this will need to intereact with whatever module uses behavioral data to update the morph line limits
//		
//		return s;
//	}
//	
	// ----- done: old versions -------	
	
	// ----- new versions --------
		
//	public void generateBehavTrainingRun() {
//		// this generates stimuli and then packages them
//		// to generate stims I need: 'match' and 'all' categories, % matches, num repeats? (true repeats or just repeat kind?)
//		// 		also: stimType, BehavioralClass (match,non-match, sample?),Behavioral category, trial sub-type 
//
//		// WHICH CATEGORIES OF STIM TO USE? -- 0 to 7 for each stimulus type -- eventually, after training, allCats and matchCats will both be {0,...,7}
//		int[] allCats   = new int[]{0,1,2,3,4,5,6,7};	// these are all categories used (samples and distractors)
//		int[] matchCats = new int[]{0,1,2,3,4,5,6,7};	// these are the categories that will be matched
//		
////		int numMatchRepeats = 5;			// # times a A-A matching pair is shown
////		int numUniqueNonMatchRepeats = 1;	// # times a unique A-B non-matching pair is shown
//		
//		double percMatches = 0.5;
//		int numRepsPerCat = 1;
//		
//		// create stims and return stimIds -- IMPORTANT, stimIds will need to be kept together as pairs!
//		generateBehavTaskStims(allCats,matchCats,percMatches,numRepsPerCat); // add trial sub-cat?
//			// this returns what? the stimObjIDs for obj A and B (1st and 2nd objects in matched/non-matched pair)
//			// 
//
//		
//		// create trials --shuffle stim pairs (redundant when using randomly generated stimuli, but will use later)	
//		
//	}
	
//	private void generateBehavTaskStims(int[] allCats, int[] matchCats, double percentMatches, int numRepsPerCat) {
//		
//		// want to do this X times: once for each matchCat X numRepeats?
//		// output? ahhh
//		// how did I want to do this for the experiment/morphs? 
//		//  want morph line distribution, defined by sigma. use this distribution to (randomly) choose the morph amount 
//		//  for each stim (for matches this is straightforward, but also do this for non-matches?)
//		// --> if I do it this way, do I still want to purposefully cover (equally) all match categories? or leave it to chance?
//		//     to cover all categories, I'd need to first generate all stims, then shuffle them (as for GA)
//		
//		
//		// TRIAL SETUP 
//		int targetIndex = -1;					// default: no target
//		
//		// MATCH/NON-MATCH PROPORTIONS 
//		targetIndex = SachMathUtil.randBoolean(percentMatches) ? 0 : -1;
//		
//		// WHICH TYPE OF STIM TO USE?	
//		StimType type = StimType.BEH_MedialAxis;					// only using medial-axis defined stimuli for now
//		
//		
//		// create matches:
//		
//		BehavioralClass behavClass = BehavioralClass.SAMPLE;
//		for (int cat : matchCats) {
//			createBehavStimFromCat(type,cat,behavClass);
//		}
//		
////		// CREATE SAMPLE STIMULUS
////		BsplineObjectSpec s_sample;
////
////		if (targetIndex >= 0) {											// if it's a match trial, use a match category
////			s_sample = generateBehavStim(type,matchCats,BehavioralClass.SAMPLE);
////		} else { 														// otherwise, use any category
////			s_sample = generateBehavStim(type,allCats,BehavioralClass.SAMPLE);		
////		}
////		
////		// CREATE TEST (MATCH/NON-MATCH) STIMULUS
////		// first remove the sample category from the categories array (so that the non-matches/distractors don't use the sample category)
////		int sampleCatUsed = s_sample.getCategory();
////		int[] nonMatchCats = SachMathUtil.removeElement(allCats, sampleCatUsed);
////	
////		BsplineObjectSpec s_test;
////		if (targetIndex >= 0) {								// create match
////			s_test = generateBehavStim(type,new int[]{sampleCatUsed},BehavioralClass.MATCH);
////		} else {											// create non-match
////			s_test = generateBehavStim(type,nonMatchCats,BehavioralClass.NON_MATCH);
////		}
//		
//	}
	
//	public SachExptSpec generateBehTrial_training(int[] allCats, int[] matchCats, double percentMatches) {
//		// -- this method randomly chooses whether this is a match or non-match trial, then randomly picks 
//		// stim categories appropriately
//
//		// WHICH TYPE OF STIM TO USE?	
//		BehavioralClass behClass_test = null;
//		int cat_test, cat_sample;
//		
//		// MATCH or NON-MATCH trial (0 = match, -1 = no match):
//		int targetIndex = SachMathUtil.randBoolean(percentMatches) ? 0 : -1;
//		
//		// CHOOSE STIM CATEGORIES:
//		
//		if (targetIndex >= 0) { 	//match trial 
//			behClass_test = BehavioralClass.MATCH;
//			cat_test = matchCats[SachMathUtil.randRange(matchCats.length-1,0)];	// randomly pick test category from among matchCats
//			cat_sample = cat_test;												// sample category same as test (match)
//		} else {					//non-match trial 
//			behClass_test = BehavioralClass.NON_MATCH;
//			cat_test = allCats[SachMathUtil.randRange(allCats.length-1,0)];		// randomly pick test category from among allCats
//			int[] nonMatchCats = SachMathUtil.removeElement(allCats, cat_test);	// remove cat_test from allCats
//			cat_sample = nonMatchCats[SachMathUtil.randRange(nonMatchCats.length-1,0)];	// pick sample category from among (allCats-catA) (non-match!)
//		}
//		
//		SachExptSpec g = genBehTrialFromCats(cat_test,cat_sample,targetIndex, behClass_test,TrialType.BEH_train);
//		return g;
//		
//	}
	
	
//	public SachExptSpec genBehTrialFromCats(int cat_test, int cat_sample, int targetIdx, BehavioralClass behClass, TrialType trialType) {
//		
//		StimType type = StimType.BEH_MedialAxis;	// only using medial-axis defined stimuli for now
//		
//		BsplineObjectSpec spec_test = createBehavStimFromCat(type,cat_test,behClass,trialType);
//		BsplineObjectSpec spec_sample = createBehavStimFromCat(type,cat_sample,BehavioralClass.SAMPLE,trialType);
//
//		System.out.println("BehTrial: test=" + cat_test + " sample=" + cat_sample);
//		
//		// test stimulus is shown first, then the sample (or reference) stimulus
//		// [this allows that the neural response to the test stimulus be unaffected by any expectation caused
//		//  by the sample stimulus]
//		return createBehTrial(spec_test.getStimObjId(),spec_sample.getStimObjId(),targetIdx);
//	}
//	
//	private BsplineObjectSpec createBehavStimFromCat(StimType type, int category, BehavioralClass behavClass, TrialType trialType) {
//		// given stim type, category, and behavioral class (sample, match), generate stim spec
//		boolean jitterPosition = false;
//		boolean doRandLengths = false;
//		boolean doMorphs = false;
//		double morphLim = morphLineLimit;	// *** implement this ***
//		// TODO:when morph lines are spec'ed out in BsplineObjectSpec, need to keep track of morph line
//		//		limits for each category this will need to intereact with whatever module uses
//		//		behavioral data to update the morph line limits
//
//		
//		// STIMULUS SETUP
//		BsplineObjectSpec s = new BsplineObjectSpec();
//		SachStimDataEntry d = new SachStimDataEntry();
//		
//		double xCntr = 0;	// defaults
//		double yCntr = 0;										
//		float size = 4;										
//		
//		if (jitterPosition) {
//			xCntr += Math.random() * 10 - 5;	// for randomly jittering the position of stimuli
//			yCntr += Math.random() * 10 - 5;
//		}
//		
//		// GENERATE STIM	
//		long stimObjId = globalTimeUtil.currentTimeMicros();
//		
//		// -- set spec values 		
//		s.setStimObjId(stimObjId);
//		s.setStimType(type.toString());
//		s.setBehavioralClass(behavClass.toString());
//		s.setCategory(category);
//		s.setXCenter(xCntr);
//		s.setYCenter(yCntr);
//		s.setSize(size);
//		s.setAnimation(false);
//		s.setDoRandom(doRandLengths);	// randomly change the lengths (and/or widths) of behavioral simuli
//		s.setDoMorph(doMorphs);			// randomly choose object parameters from morph line TODO: remove this and just control w morphLim?
//		s.setMorphLim(morphLim);		// current limit set for morph line 		
//		
//		// -- need to re-create object spec after running it through the object (BsplineObject), (this saves the limbs info with the spec):
//		BsplineObject obj = new BsplineObject();
//		obj.setSpec(s.toXml());
//		BsplineObjectSpec ss = obj.getSpec();
//		
//		// -- set data values
//		d.setStimObjId(stimObjId);
//		d.setTrialType(trialType.toString());
//		
//		// create SachStimDataEntry, then write to DB
//		dbUtil.writeStimObjData(stimObjId, ss.toXml(), d.toXml());
//				
//		return s;
//	}
//	
//	public long generateBehStimFromCat(int category) {
//		
//		BsplineObjectSpec s = createBehavStimFromCat(StimType.BEH_MedialAxis,category,BehavioralClass.NA,TrialType.BEH_quick);
//		return s.getStimObjId();
//		
//	}
//	
//	private SachExptSpec createBehTrial(long stimObjId_A, long stimObjId_B, int targetIndex) {
//			
//		// TRIAL INIT 
//		SachExptSpec g = new SachExptSpec(); 	// spec for each trial
//		
//		// ADD STIMULI TO TRIAL
//		g.addStimObjId(stimObjId_A);			
//		g.addStimObjId(stimObjId_B);
//		g.setTargetIndex(targetIndex);			// targetIndex indicates which object is the target, if no target then it is -1 and fixation at end of trial is rewarded
//		
//		// TRIAL SPECS
//			// for setting the target position to the 'disk' saccadic response spot
//		double pos_x = 0, pos_y = 0;								// default target position
//		if (targetIndex != -1) {									// map target position to the response spot, if no target then just reward fixation
//			pos_x = renderer.mm2deg(DiskObject.getTx());	// set target position to the position of the response disk (see SachExptScene) in deg
//			pos_y = renderer.mm2deg(DiskObject.getTy());
//		}
//		
//		g.setTrialType(trialType.toString());						// shows whether trial is Behavioral or GA
//		g.setTargetPosition(new Coordinates2D(pos_x, pos_y));		// (in degrees)
//		g.setTargetEyeWinSize(targetEyeWindowSize);					// use this to change accuracy tolerance (in degrees)
//		//g.setReward((long)(Math.random() * 100 + 100));			// randomize reward size
//		g.setReward(rewardAmount);									// fixed reward size
//		
//		return g;	
//	}
	

	// --------------------------------
	// ---- GA stimulus generation ----
	// --------------------------------
	
	public List<Long> getAllBlankStimIds(Long gen) {
		List<Long> stimObjIds = new ArrayList<Long>();
		
		String prefix = dbUtil.readCurrentDescriptivePrefix();
		Long id1 = dbUtil.readStimObjIdFromDescriptiveId(new String(prefix + "_g-" + gen.toString() + "_s-BLANK"));
			
		stimObjIds.add(id1); 
		return stimObjIds;
	}
	
	public List<Long> getAllStimIds(Long gen, int numNonBlankStim) {
		List<Long> stimObjIds = new ArrayList<Long>();
		
		String prefix = dbUtil.readCurrentDescriptivePrefix();
		
		for (int j=1; j<=numNonBlankStim; j++) {
			Long id1 = dbUtil.readStimObjIdFromDescriptiveId(new String(prefix + "_g-" + gen.toString() + "_l-1_s-" + j));
			Long id2 = dbUtil.readStimObjIdFromDescriptiveId(new String(prefix + "_g-" + gen.toString() + "_l-2_s-" + j));
				
			stimObjIds.add(id1); stimObjIds.add(id2);
		}
		
		return stimObjIds;
	}
	
//	public List<Long> getAllFingerprintingStimIds(Long gen, int numFingerprintingStim) {
//		List<Long> fingerprintingStimObjIds = new ArrayList<Long>();
//		
//		String prefix = dbUtil.readCurrentDescriptivePrefix();
//		
//		for (int j=1; j<=numFingerprintingStim; j++) {
//			Long id1 = dbUtil.readStimObjIdFromDescriptiveId(new String(prefix + "_g-" + gen + "_f_s-" + j));
//			fingerprintingStimObjIds.add(id1);
//		}
//		
//		return fingerprintingStimObjIds;
//	}
//	
//	public long generateMorphStim(long gen, int lineage, long parentId) {
//		
//		// PARENT STIM
//		BsplineObjectSpec parentSpec = BsplineObjectSpec.fromXml(dbUtil.readStimSpecFromStimObjId(parentId).getSpec());
//		
//		
//		// STIMULUS SETUP
//		BsplineObjectSpec s = new BsplineObjectSpec();
//		SachStimDataEntry d = new SachStimDataEntry();
//		
//		double xCntr = 0;											// defaults
//		double yCntr = 0;										
//		double size = parentSpec.getSize();										
//
//		xCntr += Math.random() * 10 - 5;							// for randomly jittering the position of stimuli
//		yCntr += Math.random() * 10 - 5;
//
//		// GENERATE STIM	
//		long stimObjId = globalTimeUtil.currentTimeMicros();
//
//		// -- set spec values 		
//		s.setStimObjId(stimObjId);
//		s.setStimType(StimType.GA.toString());
//		s.setXCenter(xCntr);
//		s.setYCenter(yCntr);
//		s.setSize(size);
//		s.setAnimation(false);
//		s.setDoMorph(true);									// morph parent limbs
//		s.setCPts(parentSpec.getCPts());	// pass parent limbs
//		
//		
//		// want to re-create object spec after running it through the object (BsplineObject), (this saves the limbs info with the spec):
//		BsplineObject obj = new BsplineObject();
//		obj.setSpec(s.toXml());
//		BsplineObjectSpec ss = obj.getSpec();
//
//		// -- set data values
//		d.setStimObjId(stimObjId);
//		d.setTrialType(TrialType.GA.toString());
//		d.setBirthGen(gen);
//		d.setLineage(lineage);
//		d.setParentId(parentId);
//		
//		// create stimObjId and add it to this and SachStimDataEntry, then write them to the DB
//		dbUtil.writeStimObjData(stimObjId, ss.toXml(), d.toXml());
//		
//		return stimObjId;
//	}

	public SachExptSpec generateGATrial(List<Long> stimObjIds, String trialType) {
		
		// TRIAL SETUP 
		SachExptSpec g = new SachExptSpec(); 	// spec for each trial
		int numObjects = stimObjIds.size();		// number of objects in this trial
		
		// ADD STIMULI TO TRIAL
		for (int n=0;n<numObjects;n++) {
			g.addStimObjId(stimObjIds.get(n));
		}
				
		// TRIAL SPECS
		g.setTrialType(trialType);						// shows whether trial is Behavioral or GA
//		g.setTargetPosition(new Coordinates2D(0, 0));	// 'target position' is same as fixation when no target (in degrees) -- (maybe load these values directly in case fixation changes?)
//		g.setTargetEyeWinSize(targetEyeWindowSize);			// use this to change accuracy tolerance (in degrees)
		g.setReward(rewardAmount);						// fixed reward size
//		g.setTargetIndex(-1);							// targetIndex indicates which object is the target, if no target then it is -1 and fixation at end of trial is rewarded
				
		return g;
	}

//	private void writeStimObjDataToDb(long stimObjId,BsplineObjectSpec s,SachStimDataEntry d,BsplineObject o) {
//		// first, if we are saving PNG thumbnails, do it here:
//		// TODO:
//		// create PNG thumbnails
//		if (saveThumbnails) {
//			PNGmaker pngMaker = new PNGmaker(dbUtil);
////			pngMaker.MakeFromIds(stimObjId);
////			pngMaker.setSpecs(s)
////			pngMaker
//		}
//		
//		// create stimObjId and add it to this and SachStimDataEntry, then write them to the DB
//		dbUtil.writeStimObjData(stimObjId, s.toXml(), d.toXml());
//	}
	
	
	// ------------------------
	// ---- output methods ----
	// ------------------------
	
	public String generateBehTrialSpec(long stimObjId_A, long stimObjId_B, int targetIndex) {
//		return this.createBehTrial(stimObjId_A,stimObjId_B,targetIndex).toXml();
		return "";
	}
	
	public String generateGATrialSpec(List<Long> stimObjIds) {
		return this.generateGATrial(stimObjIds,TrialType.GA3D.toString()).toXml();
	}

	public String generateBEHQuickTrialSpec(List<Long> stimObjIds) {
//		return this.generateGATrial(stimObjIds,TrialType.BEH_quick.toString()).toXml();
		return "";
	}
	
	// -----------------------------
	// ---- setters and getters ----
	// -----------------------------

	public long getTaskId() {
		return taskId;
	}
	public void setTaskId(long id) {
		taskId = id;
	}

	public double getMorphLineLimit() {
		return morphLineLimit;
	}
	public void setMorphLineLimit(double morphLineLimit) {
		this.morphLineLimit = morphLineLimit;
	}

	public SachDbUtil getDbUtil() {
		return dbUtil;
	}
	public void setDbUtil(SachDbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}

	public TimeUtil getGlobalTimeUtil() {
		return globalTimeUtil;
	}
	public void setGlobalTimeUtil(TimeUtil globalTimeUtil) {
		this.globalTimeUtil = globalTimeUtil;
	}

	public AbstractRenderer getRenderer() {
		return renderer;
	}
	public void setRenderer(AbstractRenderer renderer) {
		this.renderer = renderer;
	}

	public TrialType getTrialType() {
		return trialType;
	}
	public void setTrialType(TrialType trialType) {
		this.trialType = trialType;
	}
	
}
