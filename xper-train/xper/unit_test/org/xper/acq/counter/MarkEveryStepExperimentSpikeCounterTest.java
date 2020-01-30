package org.xper.acq.counter;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.SortedMap;

import junit.framework.TestCase;

import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.xper.XperConfig;
import org.xper.acq.vo.DigitalChannel;
import org.xper.db.vo.AcqDataEntry;
import org.xper.db.vo.SystemVariable;
import org.xper.db.vo.TaskDoneEntry;
import org.xper.time.DefaultTimeUtil;
import org.xper.time.TimeUtil;
import org.xper.util.DbUtil;

public class MarkEveryStepExperimentSpikeCounterTest extends TestCase {
	protected void setUp() throws Exception {
		super.setUp();
		
		List<String> libs = new ArrayList<String>();
		libs.add("xper");
		new XperConfig("", libs);
	}
	
	protected void tearDown() throws Exception {
		super.tearDown();
	}
	
	public void testSingleUpEdgeAtTheEnd() {
		DriverManagerDataSource dataSource = new DriverManagerDataSource();
		dataSource.setDriverClassName("com.mysql.jdbc.Driver");
		dataSource.setUrl("jdbc:mysql://192.168.1.1/sach_ecpc48_2014_04_25_testing");
		dataSource.setUsername("xper_rw");
		dataSource.setPassword("up2nite");

		DbUtil dbUtil = new DbUtil();
		dbUtil.setDataSource(dataSource);
		
		TimeUtil timeUtil = new DefaultTimeUtil();
		
		Map<String,SystemVariable> vars = dbUtil.readSystemVar("%");
		short evenMarkerChannel = Short.parseShort(vars.get("acq_even_marker_chan").getValue(0));
		short oddMarkerChannel = Short.parseShort(vars.get("acq_odd_marker_chan").getValue(0));
		short dataChannel = Short.parseShort(vars.get("acq_data_chan").getValue(0));
		
		long sessionStart = timeUtil.currentTimeMicros();
		long sessionStop = sessionStart + 100;
		
		dbUtil.writeBeginAcqSession(sessionStart);
		long task1 = sessionStart + 10;
		dbUtil.writeTaskDone(task1, task1, 0);
		
		// even up
		ArrayList<AcqDataEntry> data = new ArrayList<AcqDataEntry>();
		AcqDataEntry ent = new AcqDataEntry();
		ent.setChannel ( (short)evenMarkerChannel);
		ent.setSampleInd ( 0);
		ent.setValue (DigitalChannel.UP);
		data.add(ent);
		
		int spike1Up = 20;
		ent = new AcqDataEntry();
		ent.setChannel ( (short)dataChannel);
		ent.setSampleInd ( spike1Up);
		ent.setValue (DigitalChannel.UP);
		data.add(ent);
		
		int spike1Down = 22;
		ent = new AcqDataEntry();
		ent.setChannel ( (short)dataChannel);
		ent.setSampleInd ( spike1Down);
		ent.setValue (DigitalChannel.DOWN);
		data.add(ent);
		
		// even down
		ent = new AcqDataEntry();
		ent.setChannel ( (short)evenMarkerChannel);
		ent.setSampleInd ( 100);
		ent.setValue (DigitalChannel.DOWN);
		data.add(ent);
		
		// odd up
		ent = new AcqDataEntry();
		ent.setChannel ( (short)oddMarkerChannel);
		ent.setSampleInd ( 110);
		ent.setValue (DigitalChannel.UP);
		data.add(ent);
		
		dbUtil.writeAcqData(sessionStop - 1, data);
		
		dbUtil.writeEndAcqSession(sessionStart, sessionStop);
		
		List<TaskDoneEntry> tasks = dbUtil.readTaskDoneByTimestampRange(sessionStart, sessionStop);
		MarkEveryStepExperimentSpikeCounter spikeCounter = new MarkEveryStepExperimentSpikeCounter();
		spikeCounter.setDbUtil(dbUtil);

		SortedMap<Long, MarkEveryStepTaskSpikeDataEntry> result = spikeCounter.getTaskSpike(tasks, dataChannel);

		//XStream stream = new XStream();
		//System.out.println(stream.toXML(result));
		
		MarkEveryStepTaskSpikeDataEntry e = result.get(task1);
		assertEquals((spike1Up + spike1Down) / 2, e.getTrialStageData(0).getSpikeData()[0]);
		assertEquals(2, e.getTrialStageData().size());
	}
	
	public void testNoDownEdgeAtTheEnd() {
		DriverManagerDataSource dataSource = new DriverManagerDataSource();
		dataSource.setDriverClassName("com.mysql.jdbc.Driver");
		dataSource.setUrl("jdbc:mysql://192.168.1.1/sach_ecpc48_2014_04_25_testing");
		dataSource.setUsername("xper_rw");
		dataSource.setPassword("up2nite");

		DbUtil dbUtil = new DbUtil();
		dbUtil.setDataSource(dataSource);
		
		TimeUtil timeUtil = new DefaultTimeUtil();
		
		Map<String,SystemVariable> vars = dbUtil.readSystemVar("%");
		short evenMarkerChannel = Short.parseShort(vars.get("acq_even_marker_chan").getValue(0));
		short oddMarkerChannel = Short.parseShort(vars.get("acq_odd_marker_chan").getValue(0));
		short dataChannel = Short.parseShort(vars.get("acq_data_chan").getValue(0));
		
		long sessionStart = timeUtil.currentTimeMicros();
		long sessionStop = sessionStart + 100;
		
		dbUtil.writeBeginAcqSession(sessionStart);
		long task1 = sessionStart + 10;
		dbUtil.writeTaskDone(task1, task1, 0);
		
		// even up
		ArrayList<AcqDataEntry> data = new ArrayList<AcqDataEntry>();
		AcqDataEntry ent = new AcqDataEntry();
		ent.setChannel ( (short)evenMarkerChannel);
		ent.setSampleInd ( 0);
		ent.setValue (DigitalChannel.UP);
		data.add(ent);
		
		int spike1Up = 20;
		ent = new AcqDataEntry();
		ent.setChannel ( (short)dataChannel);
		ent.setSampleInd ( spike1Up);
		ent.setValue (DigitalChannel.UP);
		data.add(ent);
		
		int spike1Down = 22;
		ent = new AcqDataEntry();
		ent.setChannel ( (short)dataChannel);
		ent.setSampleInd ( spike1Down);
		ent.setValue (DigitalChannel.DOWN);
		data.add(ent);
		
		// even down
		ent = new AcqDataEntry();
		ent.setChannel ( (short)evenMarkerChannel);
		ent.setSampleInd ( 100);
		ent.setValue (DigitalChannel.DOWN);
		data.add(ent);
		
		// odd up
		ent = new AcqDataEntry();
		ent.setChannel ( (short)oddMarkerChannel);
		ent.setSampleInd ( 110);
		ent.setValue (DigitalChannel.UP);
		data.add(ent);
		
		// odd down
		ent = new AcqDataEntry();
		ent.setChannel ( (short)oddMarkerChannel);
		ent.setSampleInd ( 120);
		ent.setValue (DigitalChannel.DOWN);
		data.add(ent);
		
		int spike2Up = 122;
		ent = new AcqDataEntry();
		ent.setChannel ( (short)dataChannel);
		ent.setSampleInd ( spike2Up);
		ent.setValue (DigitalChannel.UP);
		data.add(ent);
		
		int spike2Down = 124;
		ent = new AcqDataEntry();
		ent.setChannel ( (short)dataChannel);
		ent.setSampleInd ( spike2Down);
		ent.setValue (DigitalChannel.DOWN);
		data.add(ent);
		
		ent = new AcqDataEntry();
		ent.setChannel ( (short)oddMarkerChannel);
		ent.setSampleInd ( 130);
		ent.setValue (DigitalChannel.UP);
		data.add(ent);
		
		dbUtil.writeAcqData(sessionStop - 1, data);
		
		dbUtil.writeEndAcqSession(sessionStart, sessionStop);
		
		List<TaskDoneEntry> tasks = dbUtil.readTaskDoneByTimestampRange(sessionStart, sessionStop);
		MarkEveryStepExperimentSpikeCounter spikeCounter = new MarkEveryStepExperimentSpikeCounter();
		spikeCounter.setDbUtil(dbUtil);

		SortedMap<Long, MarkEveryStepTaskSpikeDataEntry> result = spikeCounter.getTaskSpike(tasks, dataChannel);

		//XStream stream = new XStream();
		//System.out.println(stream.toXML(result));
		
		MarkEveryStepTaskSpikeDataEntry e = result.get(task1);
		assertEquals((spike1Up + spike1Down) / 2, e.getTrialStageData(0).getSpikeData()[0]);
		
		assertEquals(0, e.getTrialStageData(1).getSpikeData().length);
		assertEquals(2, e.getTrialStageData().size());
	}
	
	public void testImcompleteSpikes() {
		DriverManagerDataSource dataSource = new DriverManagerDataSource();
		dataSource.setDriverClassName("com.mysql.jdbc.Driver");
		dataSource.setUrl("jdbc:mysql://192.168.1.1/sach_ecpc48_2014_04_25_testing");
		dataSource.setUsername("xper_rw");
		dataSource.setPassword("up2nite");

		DbUtil dbUtil = new DbUtil();
		dbUtil.setDataSource(dataSource);
		
		TimeUtil timeUtil = new DefaultTimeUtil();
		
		Map<String,SystemVariable> vars = dbUtil.readSystemVar("%");
		short evenMarkerChannel = Short.parseShort(vars.get("acq_even_marker_chan").getValue(0));
		short oddMarkerChannel = Short.parseShort(vars.get("acq_odd_marker_chan").getValue(0));
		short dataChannel = Short.parseShort(vars.get("acq_data_chan").getValue(0));
		
		long sessionStart = timeUtil.currentTimeMicros();
		long sessionStop = sessionStart + 100;
		
		dbUtil.writeBeginAcqSession(sessionStart);
		long task1 = sessionStart + 10;
		dbUtil.writeTaskDone(task1, task1, 0);
		
		// even up
		ArrayList<AcqDataEntry> data = new ArrayList<AcqDataEntry>();
		AcqDataEntry ent = new AcqDataEntry();
		ent.setChannel ( (short)evenMarkerChannel);
		ent.setSampleInd ( 0);
		ent.setValue (DigitalChannel.UP);
		data.add(ent);
		
		int spike1Up = 20;
		ent = new AcqDataEntry();
		ent.setChannel ( (short)dataChannel);
		ent.setSampleInd ( spike1Up);
		ent.setValue (DigitalChannel.UP);
		data.add(ent);
		
		int spike1Down = 22;
		ent = new AcqDataEntry();
		ent.setChannel ( (short)dataChannel);
		ent.setSampleInd ( spike1Down);
		ent.setValue (DigitalChannel.DOWN);
		data.add(ent);
		
		// even down
		ent = new AcqDataEntry();
		ent.setChannel ( (short)evenMarkerChannel);
		ent.setSampleInd ( 100);
		ent.setValue (DigitalChannel.DOWN);
		data.add(ent);
		
		// odd up
		ent = new AcqDataEntry();
		ent.setChannel ( (short)oddMarkerChannel);
		ent.setSampleInd ( 110);
		ent.setValue (DigitalChannel.UP);
		data.add(ent);
		
		int spike3Down = 111;
		ent = new AcqDataEntry();
		ent.setChannel ( (short)dataChannel);
		ent.setSampleInd ( spike3Down);
		ent.setValue (DigitalChannel.DOWN);
		data.add(ent);
		
		int spike2Up = 119;
		ent = new AcqDataEntry();
		ent.setChannel ( (short)dataChannel);
		ent.setSampleInd ( spike2Up);
		ent.setValue (DigitalChannel.UP);
		data.add(ent);
		
		// odd down
		ent = new AcqDataEntry();
		ent.setChannel ( (short)oddMarkerChannel);
		ent.setSampleInd ( 120);
		ent.setValue (DigitalChannel.DOWN);
		data.add(ent);
		
		dbUtil.writeAcqData(sessionStop - 1, data);
		
		dbUtil.writeEndAcqSession(sessionStart, sessionStop);
		
		List<TaskDoneEntry> tasks = dbUtil.readTaskDoneByTimestampRange(sessionStart, sessionStop);
		MarkEveryStepExperimentSpikeCounter spikeCounter = new MarkEveryStepExperimentSpikeCounter();
		spikeCounter.setDbUtil(dbUtil);

		SortedMap<Long, MarkEveryStepTaskSpikeDataEntry> result = spikeCounter.getTaskSpike(tasks, dataChannel);

		//XStream stream = new XStream();
		//System.out.println(stream.toXML(result));
		
		MarkEveryStepTaskSpikeDataEntry e = result.get(task1);
		assertEquals((spike1Up + spike1Down) / 2, e.getTrialStageData(0).getSpikeData()[0]);
		assertEquals(2, e.getTrialStageData().size());
		assertEquals(0.0, e.getSpikePerSec(1), 0.0001);
		assertEquals(0, e.getTrialStageData(1).getSpikeData().length);
	}
	
	public void testNoDownEdgeAtTheEndWithMoreNonMarkerSamples() {
		DriverManagerDataSource dataSource = new DriverManagerDataSource();
		dataSource.setDriverClassName("com.mysql.jdbc.Driver");
		dataSource.setUrl("jdbc:mysql://192.168.1.1/sach_ecpc48_2014_04_25_testing");
		dataSource.setUsername("xper_rw");
		dataSource.setPassword("up2nite");

		DbUtil dbUtil = new DbUtil();
		dbUtil.setDataSource(dataSource);
		
		TimeUtil timeUtil = new DefaultTimeUtil();
		
		Map<String,SystemVariable> vars = dbUtil.readSystemVar("%");
		short evenMarkerChannel = Short.parseShort(vars.get("acq_even_marker_chan").getValue(0));
		short oddMarkerChannel = Short.parseShort(vars.get("acq_odd_marker_chan").getValue(0));
		short dataChannel = Short.parseShort(vars.get("acq_data_chan").getValue(0));
		
		long sessionStart = timeUtil.currentTimeMicros();
		long sessionStop = sessionStart + 100;
		
		dbUtil.writeBeginAcqSession(sessionStart);
		long task1 = sessionStart + 10;
		dbUtil.writeTaskDone(task1, task1, 0);
		
		// even up
		ArrayList<AcqDataEntry> data = new ArrayList<AcqDataEntry>();
		AcqDataEntry ent = new AcqDataEntry();
		ent.setChannel ( (short)evenMarkerChannel);
		ent.setSampleInd ( 0);
		ent.setValue (DigitalChannel.UP);
		data.add(ent);
		
		int spike1Up = 20;
		ent = new AcqDataEntry();
		ent.setChannel ( (short)dataChannel);
		ent.setSampleInd ( spike1Up);
		ent.setValue (DigitalChannel.UP);
		data.add(ent);
		
		int spike1Down = 22;
		ent = new AcqDataEntry();
		ent.setChannel ( (short)dataChannel);
		ent.setSampleInd ( spike1Down);
		ent.setValue (DigitalChannel.DOWN);
		data.add(ent);
		
		// even down
		ent = new AcqDataEntry();
		ent.setChannel ( (short)evenMarkerChannel);
		ent.setSampleInd ( 100);
		ent.setValue (DigitalChannel.DOWN);
		data.add(ent);
		
		// odd up
		ent = new AcqDataEntry();
		ent.setChannel ( (short)oddMarkerChannel);
		ent.setSampleInd ( 110);
		ent.setValue (DigitalChannel.UP);
		data.add(ent);
		
		// odd down
		ent = new AcqDataEntry();
		ent.setChannel ( (short)oddMarkerChannel);
		ent.setSampleInd ( 120);
		ent.setValue (DigitalChannel.DOWN);
		data.add(ent);
		
		int spike2Up = 122;
		ent = new AcqDataEntry();
		ent.setChannel ( (short)dataChannel);
		ent.setSampleInd ( spike2Up);
		ent.setValue (DigitalChannel.UP);
		data.add(ent);
		
		int spike2Down = 124;
		ent = new AcqDataEntry();
		ent.setChannel ( (short)dataChannel);
		ent.setSampleInd ( spike2Down);
		ent.setValue (DigitalChannel.DOWN);
		data.add(ent);
		
		ent = new AcqDataEntry();
		ent.setChannel ( (short)oddMarkerChannel);
		ent.setSampleInd ( 130);
		ent.setValue (DigitalChannel.UP);
		data.add(ent);
		
		ent = new AcqDataEntry();
		ent.setChannel ( (short)dataChannel);
		ent.setSampleInd ( 140);
		ent.setValue (DigitalChannel.UP);
		data.add(ent);
		
		ent = new AcqDataEntry();
		ent.setChannel ( (short)dataChannel);
		ent.setSampleInd ( 150);
		ent.setValue (DigitalChannel.DOWN);
		data.add(ent);
		
		dbUtil.writeAcqData(sessionStop - 1, data);
		
		dbUtil.writeEndAcqSession(sessionStart, sessionStop);
		
		List<TaskDoneEntry> tasks = dbUtil.readTaskDoneByTimestampRange(sessionStart, sessionStop);
		MarkEveryStepExperimentSpikeCounter spikeCounter = new MarkEveryStepExperimentSpikeCounter();
		spikeCounter.setDbUtil(dbUtil);

		SortedMap<Long, MarkEveryStepTaskSpikeDataEntry> result = spikeCounter.getTaskSpike(tasks, dataChannel);

		//XStream stream = new XStream();
		//System.out.println(stream.toXML(result));
		
		MarkEveryStepTaskSpikeDataEntry e = result.get(task1);
		assertEquals((spike1Up + spike1Down) / 2, e.getTrialStageData(0).getSpikeData()[0]);
		
		assertEquals(0, e.getTrialStageData(1).getSpikeData().length);
		assertEquals(2, e.getTrialStageData().size());
	}
}
