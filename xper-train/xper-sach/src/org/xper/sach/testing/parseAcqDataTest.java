package org.xper.sach.testing;

import java.beans.PropertyVetoException;
import java.util.ArrayList;
import java.util.List;
import java.util.SortedMap;

import javax.sql.DataSource;

import org.xper.acq.counter.MarkEveryStepTaskSpikeDataEntry;
import org.xper.exception.DbException;
import org.xper.exception.InvalidAcqDataException;
import org.xper.exception.NoMoreAcqDataException;
import org.xper.sach.acq.counter.SachMarkEveryStepExptSpikeCounter;
import org.xper.sach.analysis.SachStimDataEntry;
import org.xper.sach.drawing.stimuli.BsplineObjectSpec;
import org.xper.sach.expt.SachExptSpec;
import org.xper.sach.util.SachDbUtil;

import com.mchange.v2.c3p0.ComboPooledDataSource;


public class parseAcqDataTest {


	SachDbUtil dbUtil;
	
	public void setDbUtil(SachDbUtil dbUtil_in) {
		this.dbUtil = dbUtil_in;
	}

	public static void main(String[] args) {
		
		parseAcqDataTest test = new parseAcqDataTest();

		test.setDbUtil(test.dbUtil());
		
		
		test.getSpikeResponses(10);


		
	}
	
	
	public void getSpikeResponses(long currentGen) {
		
		System.out.println("Starting getSpikeResponses... \n");

		// obtain spike data:
		long taskId;

		// use mine because it adds fake spike stuff!
		//MarkStimExperimentSpikeCounter spikeCounter = new MarkStimExperimentSpikeCounter();
		SachMarkEveryStepExptSpikeCounter spikeCounter = new SachMarkEveryStepExptSpikeCounter(); 
		spikeCounter.setDbUtil(dbUtil);

		try{
			// get spike data for all trials:
			SortedMap<Long, MarkEveryStepTaskSpikeDataEntry> spikeEntry;

//			spikeEntry = spikeCounter.getTaskSpikeByGeneration(currentGen, 0);
			spikeEntry = spikeCounter.getTaskSpikeByGeneration(currentGen, 0);
			
			// for each trial done in a generation:
				// get blank FRs:
			List<Double> blankFRs = new ArrayList<Double>();
			for (SortedMap.Entry<Long, MarkEveryStepTaskSpikeDataEntry> entry : spikeEntry.entrySet())
			{
				MarkEveryStepTaskSpikeDataEntry ent = entry.getValue();				
				taskId = ent.getTaskId();
				
				// get TrialSpec:
				SachExptSpec trialSpec = SachExptSpec.fromXml(dbUtil.getSpecByTaskId(taskId).getSpec());
				
				// for each stimObj in the trial:
				long stimObjId;
				BsplineObjectSpec spec;
				int entIdx;
				
				// first, make sure ent.whatever is long enough! this can get screwed up if part_done == 1. 
				// for some reason xper won't automatically redo these on some occasions. which? break?
				// 
				
				// first get blank stim FR data:
				for (int n=0;n<trialSpec.getStimObjIdCount();n++) {
					stimObjId = trialSpec.getStimObjId(n);
					spec = BsplineObjectSpec.fromXml(dbUtil.readStimSpecFromStimObjId(stimObjId).getSpec());
					
//					if (spec.isBlankStim()) {
//						entIdx = 2*n+2;
//						blankFRs.add(ent.getSpikePerSec(entIdx));
//					}
				}
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
				int entIdx;

				for (int n=0;n<trialSpec.getStimObjIdCount();n++) {
					stimObjId = trialSpec.getStimObjId(n);
					data = SachStimDataEntry.fromXml(dbUtil.readStimDataFromStimObjId(stimObjId).getSpec());
					
					// add acq info:					
					entIdx = 2*n+2;
					data.addTaskDoneId(taskId);
//					data.setSampleFrequency(ent.getSampleFrequency());
//					data.addSpikesPerSec(ent.getSpikePerSec(entIdx));
//					data.setBkgdSpikesPerSec(blankFRs);					// add blank FR data
//					data.addTrialStageData(ent.getTrialStageData(entIdx));
					
					// resave data:
					//dbUtil.updateStimObjData(stimObjId, data.toXml());
					System.out.println("stimObjId= " + stimObjId);
					System.out.println(data.toXml() + "\n");
				}
			}
		} catch(InvalidAcqDataException ee) {
			ee.printStackTrace();
		} catch(NoMoreAcqDataException ee) {
			ee.printStackTrace();
		}
	}
	
	

	// the following is to set the dbutil during testing, otherwise it is set via the config file(s)
	public SachDbUtil dbUtil() {
		SachDbUtil util = new SachDbUtil();
		util.setDataSource(dataSource());
		return util;
	}

	public DataSource dataSource() {
		ComboPooledDataSource source = new ComboPooledDataSource();
		try {
			source.setDriverClass("com.mysql.jdbc.Driver");
		} catch (PropertyVetoException e) {
			throw new DbException(e);
		}
		source.setJdbcUrl("jdbc:mysql://172.30.6.48/sach_ecpc48_2014_08_12_recording");
//		source.setJdbcUrl("jdbc:mysql://172.30.6.48/sach_ecpc48_2014_04_25_testing");
		source.setUser("xper_rw");
		source.setPassword("up2nite");
		return source;
	}

	
	
}
