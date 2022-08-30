package org.xper.acq.counter;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import junit.framework.TestCase;

import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.xper.XperConfig;
import org.xper.acq.vo.DigitalChannel;
import org.xper.db.vo.AcqDataEntry;
import org.xper.db.vo.SystemVariable;
import org.xper.time.DefaultTimeUtil;
import org.xper.time.TimeUtil;
import org.xper.util.DbUtil;

public class MarkStimExperimentSpikeCounterTest extends TestCase {
	protected void returnParam(int[] param) {
		int temp = param[0];
		param[0] = param[1];
		param[1] = temp;
	}

	public void testReturnParam() {
		int[] param = new int[2];
		param[0] = 100;
		param[1] = -100;
		returnParam(param);
		assertEquals(param[0], -100);
		assertEquals(param[1], 100);
	}

	public void testNormalCase() {
		List<String> libs = new ArrayList<String>();
		libs.add("xper");
		new XperConfig("", libs);
		
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
		long task2 = sessionStart + 30;
		dbUtil.writeTaskDone(task2, task2, 0);
		long task3 = sessionStart + 50;
		dbUtil.writeTaskDone(task3, task3, 0);
		long task4 = sessionStart + 70;
		dbUtil.writeTaskDone(task4, task4, 0);
		
		ArrayList<AcqDataEntry> data = new ArrayList<AcqDataEntry>();
		// task 1
		AcqDataEntry ent = new AcqDataEntry();
		ent.setChannel ( (short)evenMarkerChannel);
		ent.setSampleInd ( 0);
		ent.setValue (DigitalChannel.UP);
		data.add(ent);
		
		ent = new AcqDataEntry();
		ent.setChannel ( (short)dataChannel);
		ent.setSampleInd ( 10);
		ent.setValue (DigitalChannel.UP);
		data.add(ent);
		
		ent = new AcqDataEntry();
		ent.setChannel ( (short)dataChannel);
		ent.setSampleInd ( 12);
		ent.setValue (DigitalChannel.DOWN);
		data.add(ent);
		
		ent = new AcqDataEntry();
		ent.setChannel ( (short)evenMarkerChannel);
		ent.setSampleInd ( 100);
		ent.setValue (DigitalChannel.DOWN);
		data.add(ent);
		
		// task 2
		ent = new AcqDataEntry();
		ent.setChannel ( (short)oddMarkerChannel);
		ent.setSampleInd ( 110);
		ent.setValue (DigitalChannel.UP);
		data.add(ent);
		
		int task2Spike1Up = 120;
		ent = new AcqDataEntry();
		ent.setChannel ( (short)dataChannel);
		ent.setSampleInd ( task2Spike1Up);
		ent.setValue (DigitalChannel.UP);
		data.add(ent);
		
		int task2Spike1Down = 122;
		ent = new AcqDataEntry();
		ent.setChannel ( (short)dataChannel);
		ent.setSampleInd ( task2Spike1Down);
		ent.setValue (DigitalChannel.DOWN);
		data.add(ent);
		
		ent = new AcqDataEntry();
		ent.setChannel ( (short)dataChannel);
		ent.setSampleInd ( 130);
		ent.setValue (DigitalChannel.UP);
		data.add(ent);
		
		ent = new AcqDataEntry();
		ent.setChannel ( (short)dataChannel);
		ent.setSampleInd ( 132);
		ent.setValue (DigitalChannel.DOWN);
		data.add(ent);
		
		ent = new AcqDataEntry();
		ent.setChannel ( (short)oddMarkerChannel);
		ent.setSampleInd ( 210);
		ent.setValue (DigitalChannel.DOWN);
		data.add(ent);
		
		// task 3
		ent = new AcqDataEntry();
		ent.setChannel ( (short)evenMarkerChannel);
		ent.setSampleInd ( 220);
		ent.setValue (DigitalChannel.UP);
		data.add(ent);
		
		ent = new AcqDataEntry();
		ent.setChannel ( (short)evenMarkerChannel);
		ent.setSampleInd ( 320);
		ent.setValue (DigitalChannel.DOWN);
		data.add(ent);
		
		// task 4
		ent = new AcqDataEntry();
		ent.setChannel ( (short)oddMarkerChannel);
		ent.setSampleInd ( 330);
		ent.setValue (DigitalChannel.UP);
		data.add(ent);
		
		ent = new AcqDataEntry();
		ent.setChannel ( (short)dataChannel);
		ent.setSampleInd ( 350);
		ent.setValue (DigitalChannel.UP);
		data.add(ent);
		
		ent = new AcqDataEntry();
		ent.setChannel ( (short)dataChannel);
		ent.setSampleInd ( 352);
		ent.setValue (DigitalChannel.DOWN);
		data.add(ent);
		
		int task4StopSampleInd = 430;
		ent = new AcqDataEntry();
		ent.setChannel ( (short)oddMarkerChannel);
		ent.setSampleInd ( task4StopSampleInd);
		ent.setValue (DigitalChannel.DOWN);
		data.add(ent);
		
		ent = new AcqDataEntry();
		ent.setChannel ( (short)dataChannel);
		ent.setSampleInd ( 450);
		ent.setValue (DigitalChannel.UP);
		data.add(ent);
		
		ent = new AcqDataEntry();
		ent.setChannel ( (short)dataChannel);
		ent.setSampleInd ( 460);
		ent.setValue (DigitalChannel.DOWN);
		data.add(ent);
		
		dbUtil.writeAcqData(sessionStop - 1, data);
		
		dbUtil.writeEndAcqSession(sessionStart, sessionStop);
		

		MarkStimExperimentSpikeCounter spikeCounter = new MarkStimExperimentSpikeCounter();
		spikeCounter.setDbUtil(dbUtil);
		Map<Long, TaskSpikeDataEntry> result = spikeCounter
				.getTaskSpikeByTimestampRange(sessionStart, sessionStop, dataChannel, 0, 0);

		//XStream stream = new XStream();
		//System.out.println(stream.toXML(result));
		TaskSpikeDataEntry e = result.get(task2);
		assertEquals((task2Spike1Down + task2Spike1Up) / 2, e.getSpikeData()[0]);
		
		assertEquals(task4StopSampleInd, result.get(task4).getStopSampleIndex());
	}
}
