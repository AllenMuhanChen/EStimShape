package org.xper.util;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import junit.framework.TestCase;

import org.springframework.dao.IncorrectResultSizeDataAccessException;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.xper.XperConfig;
import org.xper.db.vo.AcqDataEntry;
import org.xper.db.vo.AcqSessionEntry;
import org.xper.db.vo.BehMsgEntry;
import org.xper.db.vo.ExpLogEntry;
import org.xper.db.vo.GenerationInfo;
import org.xper.db.vo.GenerationTaskToDoList;
import org.xper.db.vo.InternalStateVariable;
import org.xper.db.vo.RFInfoEntry;
import org.xper.db.vo.RFStimSpecEntry;
import org.xper.db.vo.StimSpecEntry;
import org.xper.db.vo.SystemVariable;
import org.xper.db.vo.TaskDoneEntry;
import org.xper.db.vo.TaskToDoEntry;
import org.xper.db.vo.XfmSpecEntry;
import org.xper.exception.VariableNotFoundException;
import org.xper.time.DefaultTimeUtil;
import org.xper.time.TimeUtil;

public class DbUtilTest extends TestCase {
	DriverManagerDataSource dataSource;
	DbUtil dbUtil;
	TimeUtil timeUtil;

	protected void setUp() throws Exception {
		super.setUp();
		
		List<String> libs = new ArrayList<String>();
		libs.add("xper");
		new XperConfig("", libs);

		dataSource = new DriverManagerDataSource();
		dataSource.setDriverClassName("com.mysql.jdbc.Driver");
		dataSource.setUrl("jdbc:mysql://192.168.1.1/sach_ecpc48_2014_04_25_testing");
		dataSource.setUsername("xper_rw");
		dataSource.setPassword("up2nite");

		dbUtil = new DbUtil();
		dbUtil.setDataSource(dataSource);

		timeUtil = new DefaultTimeUtil();
	}

	protected void tearDown() throws Exception {
		super.tearDown();
	}

	public void testAcqData() {
		// write the data
		long tstamp = timeUtil.currentTimeMicros();
		ArrayList<AcqDataEntry> write = new ArrayList<AcqDataEntry>();
		AcqDataEntry ent = new AcqDataEntry();
		ent.setChannel ( (short)1);
		ent.setSampleInd ( 100);
		ent.setValue ( -1);
		write.add(ent);
		dbUtil.writeAcqData(tstamp, write);

		// read it back
		int count = dbUtil.readAcqDataCount(tstamp, tstamp);
		assertEquals(1, count);

		List<AcqDataEntry> read = dbUtil.readAcqData(tstamp, tstamp);
		AcqDataEntry r = read.get(0);
		assertEquals(r.getChannel(), ent.getChannel());
		assertEquals(r.getSampleInd(), ent.getSampleInd());
		assertEquals(r.getValue(), ent.getValue(), 0.0001);
	}

	public void testAcqSession() {
		// write acq session
		long startTime = timeUtil.currentTimeMicros();
		try {
			Thread.sleep(100);
		} catch (InterruptedException e) {
		}
		long stopTime = timeUtil.currentTimeMicros();

		dbUtil.writeBeginAcqSession(startTime);
		dbUtil.writeEndAcqSession(startTime, stopTime);

		// read it back
		AcqSessionEntry ent = dbUtil.readAcqSession(startTime);
		assertEquals(ent.getStartTime(), startTime);
		assertEquals(ent.getStopTime(), stopTime);

		ent = dbUtil.readAcqSession(stopTime);
		assertEquals(ent.getStartTime(), startTime);
		assertEquals(ent.getStopTime(), stopTime);

		ent = dbUtil.readAcqSession(startTime, stopTime).get(0);
		assertEquals(ent.getStartTime(), startTime);
		assertEquals(ent.getStopTime(), stopTime);
	}

	public void testRepairDatabase() {
		assertEquals(Long.MAX_VALUE, 9223372036854775807L);

		// This should work even if database is good.
		dbUtil.repairAcqSession(timeUtil.currentTimeMicros());

		long startTime = timeUtil.currentTimeMicros();
		dbUtil.writeBeginAcqSession(startTime);
		dbUtil.repairAcqSession(timeUtil.currentTimeMicros());

		AcqSessionEntry ent = dbUtil.readAcqSession(startTime);
		assertTrue(ent.getStopTime() != Long.MAX_VALUE);

		try {
			ent = dbUtil.readAcqSession(Long.MAX_VALUE);
			assertTrue(false);
		} catch (IncorrectResultSizeDataAccessException e) {
			assertTrue(true);
		}
	}

	public void testBehMsg() {
		// write BehMsg
		long tstamp = timeUtil.currentTimeMicros();
		String type = "TestMsg";
		String msg = "This is a test message.";
		dbUtil.writeBehMsg(tstamp, type, msg);

		// read it back
		List<BehMsgEntry> result = dbUtil.readBehMsg(tstamp, tstamp);
		BehMsgEntry ent = result.get(0);

		assertEquals(tstamp, ent.getTstamp());
		assertEquals(type, ent.getType());
		assertEquals(msg, ent.getMsg());
	}

	public void testExpLog() {
		// write ExpLog
		long tstamp = timeUtil.currentTimeMicros();
		String memo = "This is a test log message.";
		dbUtil.writeExpLog(tstamp, memo);

		// read it back
		List<ExpLogEntry> result = dbUtil.readExpLog(tstamp, tstamp);
		ExpLogEntry ent = result.get(0);

		assertEquals(tstamp, ent.getTstamp());
		assertEquals(memo, ent.getLog());
	}

	public void testInternalState() {
		// write Internal State
		long tstamp = timeUtil.currentTimeMicros();
		String name = "TestInternalState" + tstamp;
		String val = "TestInternalState Value";
		dbUtil.writeInternalState(name, 0, val);

		// read it back
		Map<String, InternalStateVariable> result = dbUtil
				.readInternalState(name);
		InternalStateVariable var = result.get(name);

		assertEquals(name, var.getName());
		assertEquals(val, var.getValue(0));

		// update it
		String newVal = "TestInternalState new Value";
		dbUtil.updateInternalState(name, 0, newVal);

		// read it again
		result = dbUtil.readInternalState(name);
		var = result.get(name);

		assertEquals(name, var.getName());
		assertEquals(newVal, var.getValue(0));
	}

	public void testRFInfo() {
		// write it
		long tstamp = timeUtil.currentTimeMicros();
		String info = "Test RF Info";

		dbUtil.writeRFInfo(tstamp, info);

		// read it
		List<RFInfoEntry> result = dbUtil.readRFInfo(tstamp, tstamp);
		RFInfoEntry ent = result.get(0);

		assertEquals(info, ent.getInfo());
		assertEquals(tstamp, ent.getTstamp());
	}

	public void testRFStimSpec() {
		long stimId = timeUtil.currentTimeMicros();
		String spec = "Test RF Spec";

		// write it
		dbUtil.writeRFStimSpec(stimId, spec);

		// read it
		List<RFStimSpecEntry> result = dbUtil.readRFStimSpec(1);
		RFStimSpecEntry ent = result.get(0);

		assertEquals(stimId, ent.getStimId());
		assertEquals(spec, ent.getSpec());
	}

	public void testSystemVar() {
		String name = "unit_test_system_var";
		String value = "10";

		// write system variable
		long tstamp = timeUtil.currentTimeMicros();
		String newValue = "-1";
		dbUtil.writeSystemVar(name, 0, newValue, tstamp);

		// read it back
		Map<String, SystemVariable> read = dbUtil.readSystemVar(name);
		SystemVariable r = read.get(name);
		assertEquals(r.getValue(0), newValue);

		// restore the value
		tstamp = timeUtil.currentTimeMicros();
		dbUtil.writeSystemVar(name, 0, value, tstamp);

		// read it back again
		read = dbUtil.readSystemVar(name);
		r = read.get(name);
		assertEquals(r.getValue(0), value);
	}

	public void testGeneration() {
		// read ready gen info
		GenerationInfo genInfo = new GenerationInfo();
		try {
			genInfo = dbUtil.readReadyGenerationInfo();
			genInfo.setGenId(genInfo.getGenId() + 1);
			genInfo.setTaskCount(1);
		} catch (VariableNotFoundException e) {
			genInfo.setGenId(0);
			genInfo.setTaskCount(1);
//			void writeReadyGenerationInfo(long genId, int taskCount, int stimPerLinCount, int stimPerTrial,
//					int repsPerStim, boolean enableFingerprinting, int numFingerprintingStim, int numFingerprintingRepsPerChunk,
//					boolean isBubbles) {
			dbUtil.writeReadyGenerationInfo(genInfo.getGenId(),genInfo.getTaskCount());
		}

		long maxGenId = dbUtil.readTaskToDoMaxGenerationId();
		if (maxGenId >= genInfo.getGenId()) {
			genInfo.setGenId(maxGenId + 1);
		}
		maxGenId = dbUtil.readTaskDoneMaxGenerationId();
		if (maxGenId >= genInfo.getGenId()) {
			genInfo.setGenId(maxGenId + 1);
		}

//		void writeReadyGenerationInfo(long genId, int taskCount, int stimPerLinCount, int stimPerTrial,
//				int repsPerStim, boolean enableFingerprinting, int numFingerprintingStim, int numFingerprintingRepsPerChunk,
//				boolean isBubbles) {
		
		// update ready gen info
		dbUtil.updateReadyGenerationInfo(genInfo.getGenId(), genInfo.getTaskCount());

		// read gen info again
		GenerationInfo newGenInfo = dbUtil.readReadyGenerationInfo();
		assertEquals(genInfo.getGenId(), newGenInfo.getGenId());
		assertEquals(genInfo.getTaskCount(), newGenInfo.getTaskCount());

		// data for new gen
		String stimSpec = "Stimulus";
		String xfmSpec = "Xfm";
		long stimId = timeUtil.currentTimeMicros();
		long xfmId = timeUtil.currentTimeMicros();
		long taskId = timeUtil.currentTimeMicros();

		// stim spec
		dbUtil.writeStimSpec(stimId, stimSpec);

		// read
		Map<Long, StimSpecEntry> result1 = dbUtil.readStimSpec(stimId, stimId);
		StimSpecEntry ent1 = result1.get(new Long(stimId));
		assertEquals(ent1.getSpec(), stimSpec);
		assertEquals(ent1.getStimId(), stimId);

		// read again
		StimSpecEntry ent2 = dbUtil.readStimSpec(stimId);
		assertEquals(ent2.getSpec(), stimSpec);
		assertEquals(ent2.getStimId(), stimId);

		// max stim id
		long maxId = dbUtil.readStimSpecMaxId();
		assertEquals(maxId, stimId);

		// xfm spec
		dbUtil.writeXfmSpec(xfmId, xfmSpec);

		// read
		Map<Long, XfmSpecEntry> result4 = dbUtil.readXfmSpec(xfmId, xfmId);
		XfmSpecEntry ent4 = result4.get(new Long(xfmId));
		assertEquals(ent4.getSpec(), xfmSpec);
		assertEquals(ent4.getXfmId(), xfmId);

		// read again
		XfmSpecEntry ent5 = dbUtil.readXfmSpec(xfmId);
		assertEquals(ent5.getSpec(), xfmSpec);
		assertEquals(ent5.getXfmId(), xfmId);

		// max xfm id
		maxId = dbUtil.readXfmSpecMaxId();
		assertEquals(maxId, xfmId);

		// task to do
		dbUtil.writeTaskToDo(taskId, stimId, xfmId, genInfo.getGenId());

		// read
		GenerationTaskToDoList result7 = dbUtil
				.readTaskToDoByGeneration(genInfo.getGenId());
		assertEquals(result7.getGenId(), genInfo.getGenId());
		TaskToDoEntry ent7 = result7.getTask(0);
		assertEquals(ent7.getTaskId(), taskId);
		assertEquals(ent7.getStimId(), stimId);
		assertEquals(ent7.getXfmId(), xfmId);

		// max id
		maxId = dbUtil.readTaskToDoMaxId();
		assertEquals(maxId, taskId);

		// max gen id
		maxId = dbUtil.readTaskToDoMaxGenerationId();
		assertEquals(maxId, genInfo.getGenId());

		// read gen stim
		Map<Long, StimSpecEntry> result3 = dbUtil
				.readStimSpecByGeneration(genInfo.getGenId());
		StimSpecEntry ent3 = result3.get(new Long(stimId));
		assertEquals(ent3.getSpec(), stimSpec);
		assertEquals(ent3.getStimId(), stimId);

		// read xfm stim
		Map<Long, XfmSpecEntry> result6 = dbUtil
				.readXfmSpecByGeneration(genInfo.getGenId());
		XfmSpecEntry ent6 = result6.get(new Long(xfmId));
		assertEquals(ent6.getSpec(), xfmSpec);
		assertEquals(ent6.getXfmId(), xfmId);

		// task done
		long tstamp = timeUtil.currentTimeMicros();
		dbUtil.writeTaskDone(tstamp, taskId, 0);

		// max task done id
		maxId = dbUtil.readTaskDoneMaxId();
		assertEquals(taskId, maxId);

		// task done timestamp
		long ts = dbUtil.readTaskDoneTimestamp(taskId);
		assertEquals(tstamp, ts);

		// task done max gen id
		long genId = dbUtil.readTaskDoneMaxGenerationId();
		assertEquals(genInfo.getGenId(), genId);

		// task done ts range
		List<TaskDoneEntry> result8 = dbUtil.readTaskDoneByTimestampRange(
				tstamp, tstamp);
		TaskDoneEntry ent8 = result8.get(0);
		assertEquals(ent8.getTaskId(), taskId);
		assertEquals(ent8.getTstamp(), tstamp);

		// task done id range
		List<TaskDoneEntry> result9 = dbUtil.readTaskDoneByIdRange(taskId,
				taskId);
		TaskDoneEntry ent9 = result9.get(0);
		assertEquals(ent9.getTaskId(), taskId);
		assertEquals(ent9.getTstamp(), tstamp);
	}
}
