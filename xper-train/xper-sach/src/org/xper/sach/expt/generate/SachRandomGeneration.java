package org.xper.sach.expt.generate;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.SortedMap;
import java.util.TreeMap;

import org.xper.Dependency;
import org.xper.acq.counter.MarkEveryStepTaskSpikeDataEntry;
import org.xper.drawing.RGBColor;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.exception.InvalidAcqDataException;
import org.xper.exception.NoMoreAcqDataException;
import org.xper.exception.VariableNotFoundException;
import org.xper.sach.acq.counter.SachMarkEveryStepExptSpikeCounter;
import org.xper.sach.analysis.PNGmaker;
import org.xper.sach.analysis.SachStimDataEntry;
import org.xper.sach.drawing.stimuli.BsplineObjectSpec;
import org.xper.sach.expt.SachExptSpec;
import org.xper.sach.expt.SachExptSpecGenerator;
import org.xper.sach.util.CreateDbDataSource;
import org.xper.sach.util.SachDbUtil;
import org.xper.sach.vo.SachExpLogMessage;
import org.xper.time.TimeUtil;


public class SachRandomGeneration {
	@Dependency
	SachDbUtil dbUtil;
	@Dependency
	TimeUtil globalTimeUtil;
	@Dependency
	AbstractRenderer renderer;			
	@Dependency
	SachExptSpecGenerator generator;	
	@Dependency
	int taskCount;
	

	// ---- global variables:
	boolean useFakeSpikes = false;						// (for debugging)
	boolean realExp = true;							// controls output to file of expt info
	boolean saveThumbnails = true;								// do you want to save stim thumbnails?
	boolean saveBehavioralThumbnails = false;			// save thumbnails for bahevioral stimuli
	boolean isBubblesPostHoc = false;
	
	PNGmaker pngMaker;									// set of methods for creating and saving thumbnails
	
	long genId = 1;										// tracks global genId
	long thisGenId = 1;									// track generations locally, maybe also write the generation numbers to the output file?

	// ---- global variables for Beh:
	static public enum TrialType { GA3D };				// trial types
	TrialType trialType;

	
	// ---- global variables for GA:
	int GA_maxNumGens = 10;									// maximum # of generations to run
	int GA_numNonBlankStimsPerLin = 50;//40; 				// # non-blank simuli per generation per lineage	
	int GA_numStimsPerLin = GA_numNonBlankStimsPerLin + 1;	// # random shapes (or offspring) + 1 blank, per lineage
	int GA_numRepsPerStim = 5;//5;							// # repetitions of each stimulus			
	int GA_numStimsPerTrial = 4; 							// # stimuli per trial
	static int GA_numLineages = 2;							// # separate GA lineages
	boolean GA_doStereo = false;
	
	int GA_numTrials = (int)Math.ceil((double)GA_numStimsPerLin*GA_numLineages*GA_numRepsPerStim/GA_numStimsPerTrial);

	RGBColor fColor;
	RGBColor bColor;
	
	Map<Long, Long> TaskId2TrialId = new TreeMap<Long, Long>();
	Map<Long, Long[]> TrialId2StimObjIds = new TreeMap<Long, Long[]>();
	Map<Long, BsplineObjectSpec> StimObjId2ObjSpec = new TreeMap<Long, BsplineObjectSpec>();
	
	// track stimulus objects created:
	List<Long> allStimObjIds = new ArrayList<Long>();		// all non-blank stim objs created
	List<Long> allBlankStimObjIds = new ArrayList<Long>();	// all blank stim objs created

	
	public void generateGA() {	
				
		System.out.println("Generating GA run... ");
		trialType = TrialType.GA3D;
		generator.setTrialType(trialType);	// set trialType in generator
				
//		realExp = dbUtil.isRealExpt();
		saveThumbnails = true;
		

		GA_numTrials = dbUtil.readReadyGenerationInfo().getTaskCount();
		GA_numNonBlankStimsPerLin = dbUtil.readReadyGenerationInfo().getStimPerLinCount();
		GA_numStimsPerLin = GA_numNonBlankStimsPerLin + 1;	// # random shapes (or offspring) + 1 blank, per lineage
		GA_numRepsPerStim = dbUtil.readReadyGenerationInfo().getRepsPerStim();
		GA_numStimsPerTrial = dbUtil.readReadyGenerationInfo().getStimPerTrial();
		GA_doStereo = dbUtil.readReadyGenerationInfo().getUseStereoRenderer();

		writeExptStart();

		thisGenId = getGenId(); // This increments a generation number too.
		
		System.out.println("GenNum is " + thisGenId + ".");
		
		char c = 'y';
		
		if (c=='n') {
			System.out.println("\n...ending GA");
			writeExptStop();
		}
		else {
			createNthGen();
		}
		
		writeExptGenDone();
		writeExptStop();
		
		System.out.println("\nGeneration has ended.");
	}
	
	void createNthGen() {
		thisGenId = getGenId();
		
		// -- create stimuli
		List<Long> blankStimObjIds = new ArrayList<Long>();
		List<Long> stimObjIds = new ArrayList<Long>();

		blankStimObjIds = generator.getAllBlankStimIds(thisGenId);
		stimObjIds = generator.getAllStimIds(thisGenId,GA_numNonBlankStimsPerLin);
		
		// this is a vital hack. the png maker, perhaps illegitimately, creates
		// and saves the 3d objects based on the barebones spec that matlab saved in the db
		String prefix = dbUtil.readCurrentDescriptivePrefix();
		pngMaker.setStimBackgroundColor(bColor);
		pngMaker.MakeFromIds(stimObjIds, prefix + "_g-" + thisGenId);
		
		// add blank stim objects to global list:
		allBlankStimObjIds.addAll(blankStimObjIds);
		
		// add non-blank stim objects to global list:
		allStimObjIds.addAll(stimObjIds);

		// now add blanks
		// stimObjIds.addAll(blankStimObjIds);
		
		// create trial structure, populate stimspec, write task-to-do
		createGATrialsFromStimObjs(stimObjIds,blankStimObjIds);
		
		// write updated global genId and number of trials in this generation to db:		
		dbUtil.updateReadyGenerationInfo(genId,GA_numTrials,GA_numNonBlankStimsPerLin,GA_numStimsPerTrial,
				GA_numRepsPerStim, GA_doStereo);
		
		Collections.sort(stimObjIds);
		pngMaker.lateSave(stimObjIds, prefix + "_g-" + thisGenId);
		
		// get acq info and put into db:
//		if (dbUtil.isRealExpt())
//			getSpikeResponses(genId);
		
	}
	
	void createGATrialsFromStimObjs(List<Long> stimObjIds, List<Long> blankStimObjIds) {
		// -- create trial structure, populate stimspec, write task-to-do
		
		// stim repetitions:
		List<Long> allStimObjIdsInGen = new ArrayList<Long>();
		
		int nStimInOneChunk = 100;
		int nIds = stimObjIds.size();
		int nChunk = (int)Math.ceil((double)nIds / nStimInOneChunk);
		int nBlanksPerChunk = 1;
		
		// total presentations = nStimPerLin * nReps + nFingerPStim * repsPerChunk*nChunk + nBlanksPerChunk*nReps*nChunk
		double temp_GA_numTrials = (GA_numNonBlankStimsPerLin*GA_numLineages*GA_numRepsPerStim)
				+(GA_numRepsPerStim*nBlanksPerChunk*nChunk);

		temp_GA_numTrials = Math.ceil(temp_GA_numTrials/GA_numStimsPerTrial);	
		
		if (temp_GA_numTrials != GA_numTrials) {
			System.out.println("Something wrong with the calculation of trials. Recalculating...");
			System.out.println("nTrial in db = " + GA_numTrials + "; nTrial calculated = " + temp_GA_numTrials);
			GA_numTrials = (int)temp_GA_numTrials;
		}
		
		Collections.shuffle(stimObjIds);
		
		List<Long> thisChunk;
		List<Long> thisChunkReppedAndShuffled;
		
		for (int c=0;c<nChunk;c++) {
			// c to (c+1)*nStimInOneChunk
			thisChunk = new ArrayList<Long>();
			thisChunkReppedAndShuffled = new ArrayList<Long>();
			
			int chunkStart = c*nStimInOneChunk;
			int chunkEnd = Math.min((c+1)*nStimInOneChunk,nIds);
			
			thisChunk.addAll(stimObjIds.subList(chunkStart, chunkEnd));
			thisChunk.addAll(blankStimObjIds);
			
			for (int n=0;n<GA_numRepsPerStim;n++) {
				thisChunkReppedAndShuffled.addAll(thisChunk);
			}
			
			Collections.shuffle(thisChunkReppedAndShuffled);
			allStimObjIdsInGen.addAll(thisChunkReppedAndShuffled);
		}

		// create trials using shuffled stimuli:
		long taskId;
		int stimCounter = 0;

		for (int n=0;n<GA_numTrials;n++) {
			taskId = globalTimeUtil.currentTimeMicros();

			// create trialspec using sublist and taskId
			
			int endIdx = stimCounter + GA_numStimsPerTrial;
			while (endIdx>allStimObjIdsInGen.size()) endIdx--;	// this makes sure there's no out index of bounds exception

			String spec = generator.generateGATrialSpec(allStimObjIdsInGen.subList(stimCounter,endIdx));

			// save spec and tasktodo to db
			dbUtil.writeStimSpec(taskId, spec);
			dbUtil.writeTaskToDo(taskId, taskId, -1, genId);

			if(n==0)
				writeExptFirstTrial(taskId);
			else if(n==GA_numTrials-1)
				writeExptLastTrial(taskId);
			
			stimCounter = endIdx;
			try {
				Thread.sleep(10);
			} catch (InterruptedException e) {
				// TODO Auto-generated catch block
				e.printStackTrace();
			}
		}
	}
	
	
	public void getSpikeResponses(long currentGen) {
		
		long lastTrialToDo;
		long lastTrialDone;

		// first, wait for some time to make sure previous 'TaskToDo's are written to the db (the stimuli need to be presented anyway):
		try
		{	Thread.sleep(8000);	}
		catch (Exception e) {System.out.println(e);}
		
		// Wait for spike data collection to be completed:	
		int counter = 0;
		System.out.print("Waiting for ACQ process.");
		while (true)
		{
			lastTrialToDo = dbUtil.readTaskToDoMaxId();
			lastTrialDone = dbUtil.readTaskDoneCompleteMaxId();
			if ( counter % 20 == 0)
				System.out.print(".");
			counter++;
			if ( lastTrialToDo == lastTrialDone) { // Completed the tasks in this generation:
				try
				{	Thread.sleep(3000);	}
				catch (Exception e) {System.out.println(e);}
				System.out.println();
				break;
			}
			try
			{	Thread.sleep(300);	}
			catch (Exception e) {System.out.println(e);}
		}		

		
		// by now, all tasks to do have been done.
		long taskId;

		SachMarkEveryStepExptSpikeCounter spikeCounter = new SachMarkEveryStepExptSpikeCounter(); 
		ArrayList<Set<SortedMap.Entry<Long, MarkEveryStepTaskSpikeDataEntry>>> entriesList = new ArrayList<Set<SortedMap.Entry<Long, MarkEveryStepTaskSpikeDataEntry>>>();
		
		spikeCounter.setDbUtil(dbUtil);
		spikeCounter.setDbUtilSach(dbUtil);

		List<BufferedWriter> respFileWriter = new ArrayList<BufferedWriter>();
		List<BufferedWriter> backupFileWriter = new ArrayList<BufferedWriter>();
		
		try{
			// get spike data for all trials:
			List<SortedMap<Long, MarkEveryStepTaskSpikeDataEntry>> spikeEntryList = new ArrayList<SortedMap<Long, MarkEveryStepTaskSpikeDataEntry>>();
			int channelNumList[] = {0, 8, 9, 10};
			
			
			for (int iii=0; iii<4; iii++) {
				if (useFakeSpikes) {
					// this populates fake spike rates for trials 
					spikeEntryList.add(spikeCounter.getFakeTaskSpikeByGeneration(currentGen));
				} else {
					System.out.println("Parsing and saving data for channel " + (iii+1));
					spikeEntryList.add(spikeCounter.getTaskSpikeByGeneration(currentGen, channelNumList[iii]));
				}
				entriesList.add(spikeEntryList.get(iii).entrySet());
			}

			String folderName = dbUtil.readCurrentDescriptivePrefix();
			File dir = new File("resp/" + folderName + "_g-" + currentGen);
			dir.mkdirs();
			
			for (int channel=0; channel<4; channel++) {
				String channelRespBlob = "";
				String fullFilePath = "resp/" + folderName + "_g-" + currentGen + "/resp_c" + (channel+1) + ".txt";
				String backupFilePath = "resp/" + folderName + "_g-" + currentGen + "/aresp_c" + (channel+1) + ".txt";
				File respFile = new File(fullFilePath);
				if (!respFile.exists()) {
					respFile.createNewFile();
				}
				
				File backupFile = new File(backupFilePath);
				if (!backupFile.exists()) {
					backupFile.createNewFile();
				}
				
				respFileWriter.add(new BufferedWriter(new FileWriter(respFile.getAbsoluteFile())));
				backupFileWriter.add(new BufferedWriter(new FileWriter(backupFile.getAbsoluteFile())));
				
				System.out.println("Channel " + (channel+1));
				Set<SortedMap.Entry<Long, MarkEveryStepTaskSpikeDataEntry>> currentEntrySet = entriesList.get(channel);
				for (SortedMap.Entry<Long, MarkEveryStepTaskSpikeDataEntry> entry : currentEntrySet) {
					MarkEveryStepTaskSpikeDataEntry ent = entry.getValue();				
					taskId = ent.getTaskId();
	
//					System.out.println("Entering spike info for trial: " + taskId);
					
					// get TrialSpec:
					SachExptSpec trialSpec = SachExptSpec.fromXml(dbUtil.getSpecByTaskId(taskId).getSpec());
					
					// for each stimObj in the trial get FR data for all stims and save:
					long stimObjId;
					SachStimDataEntry data;
					
					
					int entIdx;
	
					for (int n=0;n<trialSpec.getStimObjIdCount();n++) {
						stimObjId = trialSpec.getStimObjId(n);
						data = SachStimDataEntry.fromXml(dbUtil.readStimDataFromStimObjId(stimObjId).getSpec());
						String descriptiveId = dbUtil.readDescriptiveIdFromStimObjId(stimObjId);
						
						// add acq info:
						if (useFakeSpikes) 
							entIdx = n; 
						else
							entIdx = 2*n+2;
						
//						entIdx = n; 
						
						if (channel == 1)
							data.addTaskDoneId(taskId);
						
						double sps = ent.getSpikePerSec(entIdx);
						
						data.setSampleFrequency(ent.getSampleFrequency(),channel);
						data.addSpikesPerSec(sps,channel);
						data.addTrialStageData(ent.getTrialStageData(entIdx),channel);
						
						respFileWriter.get(channel).write(descriptiveId + "\t\t" + sps + "\n");
						backupFileWriter.get(channel).write(descriptiveId + "\t\t" + sps + "\n");
						
						channelRespBlob = channelRespBlob + descriptiveId + "\t\t" + sps + "\n";
						
						dbUtil.updateStimObjData(stimObjId, data.toXml());
					}
				}
				long id = globalTimeUtil.currentTimeMicros();
				dbUtil.writeRefactoredResp(id, folderName + "_g-" + currentGen, channel+1, channelRespBlob);
			}
		} catch(InvalidAcqDataException ee) {
			ee.printStackTrace();
		} catch(NoMoreAcqDataException ee) {
			ee.printStackTrace();
		} catch(IOException ee) {
			ee.printStackTrace();
		} finally {
			try {
				for (int iter=0;iter<respFileWriter.size();iter++) {
					respFileWriter.get(iter).close();
				}
            } catch (Exception e) {
            }
		}
	}

	public void getSpikeResponsesWhileRunning(long currentGen) {

		// THIS IS NOT COMPLETED (and not necessary. it would only make  things slightly faster.)
		
		long lastTrialToDo;
		long lastTrialDone;

		// Wait for spike data collection to be completed:
		// : *** change later so that it runs while data is collected? ***
		// : save thumbnail with FR to file for quick eye check of results?
		// or, better, write results to an analysis window
		
		// loop. find a new taskdone, get data, run stuff, save data,...
		
		int counter = 0;
		while (true)
		{
			lastTrialToDo = dbUtil.readTaskToDoMaxId();
			lastTrialDone = dbUtil.readTaskDoneCompleteMaxId();
			if ( counter % 20 == 0)
				System.out.println("Wait for ACQ process...");
			counter++;
			if ( lastTrialToDo == lastTrialDone) // Completed the tasks in this generation:
				break;
			try
			{	Thread.sleep(300);	}
			catch (Exception e) {System.out.println(e);}
		}		

		// obtain spike data:
		long taskId;

		//MarkStimExperimentSpikeCounter spikeCounter = new MarkStimExperimentSpikeCounter();
		SachMarkEveryStepExptSpikeCounter spikeCounter = new SachMarkEveryStepExptSpikeCounter(); 
		spikeCounter.setDbUtil(dbUtil);

		try{
			// : need to test on linux machine if I'm using the right structure
			// get spike data for all trials:
			SortedMap<Long, MarkEveryStepTaskSpikeDataEntry> spikeEntry;
			if (useFakeSpikes) {
				// this populates fake spike rates for trials 
				spikeEntry = spikeCounter.getFakeTaskSpikeByGeneration(currentGen);
			} else {
				spikeEntry = spikeCounter.getTaskSpikeByGeneration(currentGen, 0);
			}
			// for each trial done in a generation:
				// get blank FRs:
//			List<Double> blankFRs = new ArrayList<Double>();
			for (SortedMap.Entry<Long, MarkEveryStepTaskSpikeDataEntry> entry : spikeEntry.entrySet())
			{
				MarkEveryStepTaskSpikeDataEntry ent = entry.getValue();				
				taskId = ent.getTaskId();
				
				// get TrialSpec:
//				SachExptSpec trialSpec = SachExptSpec.fromXml(dbUtil.getSpecByTaskId(taskId).getSpec());
				
				// for each stimObj in the trial:
//				long stimObjId;
////				BsplineObjectSpec spec;
//				
//				// first get blank stim FR data:
//				for (int n=0;n<trialSpec.getStimObjIdCount();n++) {
//					stimObjId = trialSpec.getStimObjId(n);
////					spec = BsplineObjectSpec.fromXml(dbUtil.readStimSpecFromStimObjId(stimObjId).getSpec());
//					
////					if (spec.isBlankStim()) {
////						blankFRs.add(ent.getSpikePerSec(n));
////					}
//				}
			}
			
			for (SortedMap.Entry<Long, MarkEveryStepTaskSpikeDataEntry> entry : spikeEntry.entrySet())
			{
				MarkEveryStepTaskSpikeDataEntry ent = entry.getValue();				
				taskId = ent.getTaskId();

				System.out.println("Entering spike info for trial: " + taskId);
				
				// get TrialSpec:
				SachExptSpec trialSpec = SachExptSpec.fromXml(dbUtil.getSpecByTaskId(taskId).getSpec());
				
				// for each stimObj in the trial get FR data for all stims and save:
				long stimObjId;
				SachStimDataEntry data;

				for (int n=0;n<trialSpec.getStimObjIdCount();n++) {
					stimObjId = trialSpec.getStimObjId(n);
					data = SachStimDataEntry.fromXml(dbUtil.readStimDataFromStimObjId(stimObjId).getSpec());
					
					// add acq info:
//					data.setSampleFrequency(ent.getSampleFrequency());
//					data.addSpikesPerSec(ent.getSpikePerSec(n));
//					data.setBkgdSpikesPerSec(blankFRs);					// add blank FR data
//					data.addTrialStageData(ent.getTrialStageData(n));
					data.addTaskDoneId(taskId);
					
					// resave data:
					dbUtil.updateStimObjData(stimObjId, data.toXml());
				}
			}
		} catch(InvalidAcqDataException ee) {
			ee.printStackTrace();
		} catch(NoMoreAcqDataException ee) {
			ee.printStackTrace();
		}
	}
	
	
	
	private long getGenId() {
		// get genId from db:
		try {
			genId = dbUtil.readReadyGenerationInfo().getGenId() + 1;
//			System.out.println("(genId=" + genId + ") ");
			return genId;
		} catch (VariableNotFoundException e) {
			System.out.println("Could not find genId in database. Writing value of 0.");
			dbUtil.writeReadyGenerationInfo(genId, 0, 0, 0, 0);
			return 1;
		}
	}
	
	private void writeExptStart() {
		writeExptLogMsg("START");
	}
	
	private void writeExptStop() {
		writeExptLogMsg("STOP");
	}
	
	private void writeExptGenDone() {
		writeExptLogMsg("GEN_DONE");
	}
	
	private void writeExptFirstTrial(Long trialId) {
		writeExptLogMsg("FIRST_TRIAL=" + trialId);
		dbUtil.writeDescriptiveFirstTrial(trialId);
	}
	
	private void writeExptLastTrial(Long trialId) {
		writeExptLogMsg("LAST_TRIAL=" + trialId);
		dbUtil.writeDescriptiveLastTrial(trialId);
	}

	
	private void writeExptLogMsg(String status) {
		// write ExpLog message
		long tstamp = globalTimeUtil.currentTimeMicros();
		SachExpLogMessage msg = new SachExpLogMessage(status,trialType.toString(),thisGenId,genId,dbUtil.isRealExpt(),tstamp);
		dbUtil.writeExpLog(tstamp,SachExpLogMessage.toXml(msg));
		
		//SachTrialOutcomeMessage.toXml(new SachTrialOutcomeMessage(timestamp,"PASS",taskId))
	}
	
	public static void main(String[] args){
		SachRandomGeneration s = new SachRandomGeneration();
		CreateDbDataSource dataSourceMaker = new CreateDbDataSource();
		s.dbUtil = new SachDbUtil(dataSourceMaker.getDataSource());
		
		s.getSpikeResponses(1);

	}
	
	// ---------------------------
	// ---- Getters & Setters ----
	// ---------------------------
	
	public SachDbUtil getDbUtil() {
		return dbUtil;
	}

	public void setDbUtil(SachDbUtil dbUtil) {
		this.dbUtil = dbUtil;
		pngMaker = new PNGmaker(dbUtil);
	}

	public TimeUtil getGlobalTimeUtil() {
		return globalTimeUtil;
	}

	public void setGlobalTimeUtil(TimeUtil globalTimeUtil) {
		this.globalTimeUtil = globalTimeUtil;
	}

	public SachExptSpecGenerator getGenerator() {
		return generator;
	}

	public void setGenerator(SachExptSpecGenerator generator) {
		this.generator = generator;
	}
	
	public AbstractRenderer getRenderer() {
		return renderer;
	}

	public void setRenderer(AbstractRenderer renderer) {
		this.renderer = renderer;
	}
	
	public int getTaskCount() {
		return taskCount;
	}

	public void setTaskCount(int taskCount) {
		this.taskCount = taskCount;
	}
	
	public RGBColor getStimForegroundColor() {
		return fColor;
	}
	public void setStimForegroundColor(RGBColor fColor) {
		this.fColor = fColor;
	}
	
	public RGBColor getStimBackgroundColor() {
		return bColor;
	}
	public void setStimBackgroundColor(RGBColor bColor) {
		this.bColor = bColor;
	}
	
	public int getNumStimPerTrial() {
		return this.GA_numStimsPerTrial;
	}
	
	public void setNumStimPerTrial(int numStim) {
		this.GA_numStimsPerTrial = numStim;
		this.GA_numTrials = (int)Math.ceil((double)GA_numStimsPerLin*GA_numLineages*GA_numRepsPerStim/GA_numStimsPerTrial);
	}
}
