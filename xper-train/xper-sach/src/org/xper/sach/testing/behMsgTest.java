package org.xper.sach.testing;

import java.beans.PropertyVetoException;

import javax.sql.DataSource;

import org.xper.db.vo.GenerationTaskDoneList;
import org.xper.db.vo.TaskDoneEntry;
import org.xper.exception.DbException;
import org.xper.exception.InvalidAcqDataException;
import org.xper.exception.NoMoreAcqDataException;
import org.xper.sach.util.SachDbUtil;

import com.mchange.v2.c3p0.ComboPooledDataSource;


public class behMsgTest {


	SachDbUtil dbUtil;
	
	public void setDbUtil(SachDbUtil dbUtil_in) {
		this.dbUtil = dbUtil_in;
	}

	public static void main(String[] args) {
		
		behMsgTest test = new behMsgTest();

		test.setDbUtil(test.dbUtil());
		
		
		test.getBehMsgs(17);


		
	}
	
	
	public void getBehMsgs(long currentGen) {
		// want to use the genId to get the taskIds to get the TrialOutcomes for each (want to do this instead of using TaskIdOutcome hack)
		
		GenerationTaskDoneList taskDoneList = dbUtil.readTaskDoneByGenerationLatest(currentGen);
		long taskId;
		long tstamp;
		int partDone;

		System.out.println("----- " + taskDoneList.size() + " tasks done -----");

		for (TaskDoneEntry ent : taskDoneList.getDoneTasks()) {
			System.out.println(ent.getTaskId());
		}
		
//		for (int n=0;n<taskDoneList.size();n++) {
		for (TaskDoneEntry ent : taskDoneList.getDoneTasks()) {
			try {
				
				// get TrialOutcome and TaskIdOutcome for each taskDoneId
				taskId = ent.getTaskId();
				tstamp = ent.getTstamp();
				partDone = ent.getPart_done();
			
				System.out.println("-----------------");
				System.out.println(" taskId= " + taskId + "\n tstamp= " + tstamp + "\n partdone= " + partDone);
								
				//String taskIdOutcome = dbUtil.getTaskIdOutcomeByTaskId(taskId);
				//String trialOutcome = dbUtil.readTrialOutcomeByTaskDoneTime(tstamp);
				String trialOutcome = dbUtil.readTrialOutcomeByTaskId(taskId);
				
				
				// print out results to compare

				System.out.println();
				//System.out.println("TaskIdOutcome= " + taskIdOutcome);
				System.out.println();
				System.out.println("TrialOutcome= " + trialOutcome);
				
			
			} catch(InvalidAcqDataException ee) {
				ee.printStackTrace();
			} catch(NoMoreAcqDataException ee) {
				ee.printStackTrace();
			}
			
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
//		source.setJdbcUrl("jdbc:mysql://172.30.6.48/sach_ecpc48_2014_04_25_testing");
		source.setJdbcUrl("jdbc:mysql://127.0.0.1/xper_sach_testing");
		source.setUser("xper_rw");
		source.setPassword("up2nite");
		return source;
	}

	
	
}
