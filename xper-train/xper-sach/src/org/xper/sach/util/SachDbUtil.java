package org.xper.sach.util;


import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import javax.sql.DataSource;

import org.springframework.jdbc.core.BatchPreparedStatementSetter;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowCallbackHandler;
import org.springframework.jdbc.core.simple.ParameterizedRowMapper;
import org.springframework.jdbc.core.simple.SimpleJdbcTemplate;
import org.xper.db.vo.*;
import org.xper.exception.VariableNotFoundException;
import org.xper.sach.vo.SachGenerationInfo;
import org.xper.sach.vo.SachTrialOutcomeMessage;
import org.xper.util.DbUtil;


public class SachDbUtil extends DbUtil {

//	@Dependency
//	DataSource dataSource;
	
	public SachDbUtil() {	
	}
	
	public SachDbUtil(DataSource dataSource) {
		super();
		this.dataSource = dataSource;
	}


	/**
	 * Get current generation ready in database.
	 Gen ID is important for xper to be able to load new tasks on the fly. It will only do so if the generation Id is upticked.
	 * @return throws exception if no <code>task_to_do_gen_ready</code>
	 *         variable defined or if the format of the string value is not
	 *         correct.
	 */

	public SachGenerationInfo readReadyGenerationInfo() {
		String name = "task_to_do_gen_ready";
		Map<String, InternalStateVariable> result = readInternalState(name);
		InternalStateVariable var = result.get(name);
		if (var == null) {
			throw new VariableNotFoundException("Internal state variable '"
					+ name + "' not found.");
		}
		String genInfoXml = var.getValue(0);

		return SachGenerationInfo.fromXml(genInfoXml);
	}


	/**
	 * Update <code>task_to_do_gen_ready</code> with new genId and count
	 * value.
	 *
	 */
	public void updateReadyGenerationInfo(long genId, int taskCount, int stimPerLinCount, int stimPerTrial,
										  int repsPerStim, boolean doStereo) {
		SachGenerationInfo info = new SachGenerationInfo();
		info.setGenId(genId);
		info.setTaskCount(taskCount);
		info.setStimPerLinCount(stimPerLinCount);
		info.setStimPerTrial(stimPerTrial);
		info.setRepsPerStim(repsPerStim);
		info.setUseStereoRenderer(doStereo);

		String xml = info.toXml();

		updateInternalState("task_to_do_gen_ready", 0, xml);
	}

	/**
	 * Write ready generation in InternalState table. This is used to initialize
	 * the <code>task_to_do_gen_ready</code> variable when none is in
	 * InternalState table.
	 *
	 */

	public void writeReadyGenerationInfo(long genId, int taskCount, int stimPerLinCount, int stimPerTrial,
										 int repsPerStim) {
		SachGenerationInfo info = new SachGenerationInfo();
		info.setGenId(genId);
		info.setTaskCount(taskCount);
		info.setStimPerLinCount(stimPerLinCount);
		info.setStimPerTrial(stimPerTrial);
		info.setRepsPerStim(repsPerStim);

		String xml = info.toXml();

		writeInternalState("task_to_do_gen_ready", 0, xml);
	}

	/**
	 * Before DbUtil can be used. DataSource must be set.
	 * 
	 * See createXperDbUtil in MATLAB directory for how to create data source.
	 * 
	 * @param dataSource
	 */
	public void setDataSource(DataSource dataSource) {
		this.dataSource = dataSource;
	}
	
	// read last Trial Outcome from Beh Msg -shs
	public BehMsgEntry readBehMsgMaxTrialOutcome() {
		JdbcTemplate jt = new JdbcTemplate(dataSource);

		final ArrayList<BehMsgEntry> result = new ArrayList<BehMsgEntry>();
		jt.query("SELECT @maxtstamp:=max(tstamp) FROM BehMsg WHERE type = 'TrialOutcome';" +
				"SELECT tstamp,type,msg FROM BehMsg " + 
				"WHERE type = 'TrialOutcome' AND tstamp = @maxtstamp;", 
				new RowCallbackHandler() {
					public void processRow(ResultSet rs) throws SQLException {
						BehMsgEntry ent = new BehMsgEntry();
						ent.setTstamp(rs.getLong("tstamp")); 
						ent.setType(rs.getString("type")); 
						ent.setMsg(rs.getString("msg")); 

						result.add(ent);
					}});
		
		return result.get(0);
	}
	
	// use this one
	public BehMsgEntry getLastTrialOutcome() {
		SimpleJdbcTemplate jt = new SimpleJdbcTemplate(dataSource);
		long tstamp = jt.queryForLong("SELECT max(tstamp) FROM BehMsg WHERE type='TrialOutcome'");
		return jt.queryForObject(
				"SELECT tstamp,type,msg FROM BehMsg WHERE type='TrialOutcome' AND tstamp=?",
				new ParameterizedRowMapper<BehMsgEntry>() {
					public BehMsgEntry mapRow(ResultSet rs, int rowNum)
							throws SQLException {
						BehMsgEntry ent = new BehMsgEntry();
						
						ent.setType(rs.getString("type"));
						ent.setTstamp(rs.getLong("tstamp")); 
						ent.setMsg(rs.getString("msg")); 

						return ent;
					}},
					new Object[]{tstamp});
	}

	public String getLastTrialOutcomeMsg() {
		SimpleJdbcTemplate jt = new SimpleJdbcTemplate(dataSource);
		long tstamp = jt.queryForLong("SELECT max(tstamp) FROM BehMsg WHERE type='TrialOutcome'");
		return jt.queryForObject(
				"SELECT msg FROM BehMsg WHERE type='TrialOutcome' AND tstamp=?",
				new ParameterizedRowMapper<String>() {
					public String mapRow(ResultSet rs, int rowNum)
							throws SQLException {
						return rs.getString("msg");
					}},
				new Object[]{tstamp});
	}

	public String getTrialOutcomeByTstamp(long timestamp) {
		SimpleJdbcTemplate jt = new SimpleJdbcTemplate(dataSource);
		return jt.queryForObject(
				"SELECT msg FROM BehMsg WHERE type='TrialOutcome' AND tstamp=?",
				new ParameterizedRowMapper<String>() {
					public String mapRow(ResultSet rs, int rowNum)
							throws SQLException {
						return rs.getString("msg");
					}},
				new Object[]{timestamp});
	}
	
	public String getTaskIdOutcomeByTaskId(long taskId) {
		SimpleJdbcTemplate jt = new SimpleJdbcTemplate(dataSource);
		return jt.queryForObject(
				"SELECT msg FROM BehMsg WHERE type='TaskIdOutcome' AND tstamp=?",
				new ParameterizedRowMapper<String>() {
					public String mapRow(ResultSet rs, int rowNum)
							throws SQLException {
						return rs.getString("msg");
					}},
				new Object[]{taskId});
	}
	
	
	// TODO: want to get a trial outcome given a tstamp, where tstamp is between the start and end defining the trial wanted
	
	// readBehMsgTrialStart given a time stamp during the trial (TaskDone tstamp)
	
	// read last Trial Outcome from Beh Msg -shs	
	public long readBehMsgTrialStart(long tstamp) {
		SimpleJdbcTemplate jt = new SimpleJdbcTemplate(dataSource);
		String q = "SELECT tstamp FROM BehMsg WHERE type='TrialStart' AND tstamp < ? ORDER BY tstamp DESC LIMIT 1";
		return jt.queryForLong(q,tstamp);
	}

	// read TrialOutcome msg given TrialStart tstamp
	public String readTrialOutcomeByTrialStartTime(long tstamp) {
		SimpleJdbcTemplate jt = new SimpleJdbcTemplate(dataSource);
		String q = "SELECT msg FROM BehMsg WHERE type='TrialOutcome' AND tstamp > ? ORDER BY tstamp LIMIT 1";
		return jt.queryForObject(q, String.class, tstamp);
	}
	
	public String readTrialOutcomeByTaskDoneTime(long tstamp) {
		return readTrialOutcomeByTrialStartTime(readBehMsgTrialStart(tstamp));
	}

	// in order to check that a certain TrialOutcome belongs to a certain taskId, we need to verify this
	public String readTrialOutcomeByTaskId(long taskId) {
		long tstamp = readTaskDoneTimeLast(taskId);
		String trialOutcomeString = readTrialOutcomeByTrialStartTime(readBehMsgTrialStart(tstamp));
		SachTrialOutcomeMessage msg = SachTrialOutcomeMessage.fromXml(trialOutcomeString);
		String trialOutcome = msg.getOutcome();
		
		// checking if trialOutcome matches taskId
		long taskIdCheck = msg.getTaskID();
		if (taskIdCheck != taskId) {
			trialOutcome = "N/A";
		} 
				
		return trialOutcome;
	}
	
	public SachTrialOutcomeMessage readTrialOutcomeMsgByTaskId(long taskId) {
		long tstamp = readTaskDoneTimeLast(taskId);
		String trialOutcomeString = readTrialOutcomeByTrialStartTime(readBehMsgTrialStart(tstamp));
		SachTrialOutcomeMessage msg = SachTrialOutcomeMessage.fromXml(trialOutcomeString);
		String trialOutcome = msg.getOutcome();
		
		// checking if trialOutcome matches taskId
		long taskIdCheck = msg.getTaskID();
		if (taskIdCheck != taskId) {
			trialOutcome = "N/A";
			msg.setOutcome(trialOutcome);
		} 
		
		return msg;
	}
	
	
	public long readTaskDoneTimeLast(long taskId) {
		// last one should have part_done = 0 (i.e. it was most likely completed)
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		String q = "SELECT tstamp FROM TaskDone WHERE task_id = ? ORDER BY tstamp DESC LIMIT 1";
		return jt.queryForLong(q, new Object[] { new Long(taskId) });
	}
	
	
	
	/**
	 * Get only the latest taskDone times for each TaskId in a generation. -SHS
	 * 
	 * @param genId
	 * @return {@link GenerationTaskDoneList} empty if there is no done tasks
	 *         for the generation in database.
	 */

	public GenerationTaskDoneList readTaskDoneByGenerationLatest(long genId) {
		final GenerationTaskDoneList taskDone = new GenerationTaskDoneList();
		taskDone.setGenId(genId);
		taskDone.setDoneTasks(new ArrayList<TaskDoneEntry>());

		JdbcTemplate jt = new JdbcTemplate(dataSource);
		String q = 	"SELECT d.tstamp AS tstamp, d.task_id AS task_id, d.part_done AS part_done " +
					"FROM TaskDone d, TaskToDo t " +
					"WHERE t.gen_id = ? AND d.task_id = t.task_id AND d.tstamp IN " +
					"(SELECT max(tstamp) AS max_tstamp FROM TaskDone GROUP BY task_id) " + 
					"ORDER BY d.tstamp";
		jt.query(q, new Object[] { genId },
			new RowCallbackHandler() {
				public void processRow(ResultSet rs) throws SQLException {
					TaskDoneEntry ent = new TaskDoneEntry();
					ent.setTaskId(rs.getLong("task_id")); 
					ent.setTstamp(rs.getLong("tstamp")); 
					ent.setPart_done(rs.getInt("part_done"));
					taskDone.getDoneTasks().add(ent);
				}});
		return taskDone;
		
		
//		SELECT d.tstamp AS tstamp, d.task_id AS task_id, d.part_done AS part_done FROM TaskDone d, TaskToDo t 
//		WHERE t.gen_id = 17 AND d.task_id = t.task_id AND d.tstamp IN 
//		(
//			SELECT max(tstamp) AS max_tstamp FROM TaskDone GROUP BY task_id 
//		)
//		ORDER BY d.tstamp
	}
	
	public List<Long> readTaskDoneTimes(long genId) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		final ArrayList<Long> res = new ArrayList<Long>();
		String q1 = "SELECT d.tstamp AS tstamp " + 
					"FROM TaskDone d, TaskToDo t " + 
					"WHERE d.task_id = t.task_id AND t.gen_id = ?";	
		jt.query(q1, new Object[] { genId },
		new RowCallbackHandler() {
			public void processRow(ResultSet rs) throws SQLException {
				res.add(rs.getLong("tstamp"));
			}});
		
		return res;
	}
	
	
	
	public long readTaskDoneNextId(long currTaskId) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		//long maxId = jt.queryForLong("select max(task_id) as next_task_id from TaskDone"); 
		long nextTaskId = jt.queryForLong("select min(task_id) as next_task_id from TaskDone" +
				" where task_id > ?", 
				new Object[] {currTaskId});
		return nextTaskId;
	}
	
	/**
	 * Read the thumbnail as binary.
	 * 
	 * @param stimObjId
	 * @return thumbnail
	 */
	public byte[] readThumbnail(long stimObjId) {
		SimpleJdbcTemplate jt = new SimpleJdbcTemplate(dataSource);
		return jt.queryForObject(
				"SELECT data FROM Thumbnail WHERE id=?",
				new ParameterizedRowMapper<byte[]>() {
					public byte[] mapRow(ResultSet rs, int rowNum)
							throws SQLException {
						return rs.getBytes("data");
					}},
				new Object[]{stimObjId});
	}
	
	/**
	 * Only the first "size" elements of the array are valid, and therefore saved to database.
	 * 
	 * @param msgs
	 * @param size
	 */
	public void writeBehMsgBatch(final BehMsgEntry[] msgs, final int size) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
//		jt.batchUpdate("insert into BehMsg (tstamp, type, msg) values (?, ?, ?)", 
		jt.batchUpdate("replace into BehMsg (tstamp, type, msg) values (?, ?, ?)", // TODO: change back to insert?
				new BatchPreparedStatementSetter() {
					public int getBatchSize() {
						return size;
					}

					public void setValues(PreparedStatement ps, int i)
							throws SQLException {
						ps.setLong(1, msgs[i].getTstamp());
						ps.setString(2, msgs[i].getType());
						ps.setString(3, msgs[i].getMsg());
					}
				});
	}

	
	
	/**
	 * Get the StimId for a Task in the TaskToDo list.
	 * @param paramLong
	 * @return
	 */
	public long getStimIdByTaskId(long paramLong) {
		SimpleJdbcTemplate jt = new SimpleJdbcTemplate(dataSource);
		Map<String, Object> localMap = jt.queryForMap(" select t.stim_id as id from TaskToDo t where t.task_id = ?", new Object[] { new Long(paramLong) });
		
//		JdbcTemplate localJdbcTemplate = new JdbcTemplate(this.dataSource);
//		Map<String, Object> localMap = localJdbcTemplate.queryForMap(" select t.stim_id as id from TaskToDo t where t.task_id = ?", new Object[] { new Long(paramLong) });
		//StimSpecEntry localStimSpecEntry = new StimSpecEntry();
		long l = ((Long)localMap.get("id")).longValue();
		return l;
	}
	
	// these were added by SHS
	
	
	public void writeStimObjData(long id, String spec, String data) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update("insert into StimObjData (id, javaspec, dataspec) values (?, ?, ?)", 
				new Object[] { id, spec, data });
	}
	
	public void updateStimObjData(long id, String data) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update("update StimObjData set dataspec = ? where id = ?", 
				new Object[] { data, id });
	}
	
//	public void updateInternalState(String name, int arr_ind, String val) {
//		JdbcTemplate jt = new JdbcTemplate(dataSource);
//		jt.update("update InternalState set val = ? where name = ? and arr_ind = ?", 
//						new Object[] { val, name, arr_ind });
//	}
//	public void writeInternalState(String name, int arr_ind, String val) {
//		JdbcTemplate jt = new JdbcTemplate(dataSource);
//		jt.update("insert into InternalState (name, arr_ind, val) values (?, ?, ?)", 
//						new Object[] { name, arr_ind, val });
//	}

	
	
	/**
	 * Read particular StimSpec.
	 * 
	 * @param stimObjId
	 * @return {@link StimSpecEntry}
	 */
	public StimSpecEntry readStimSpecFromStimObjId(long stimObjId) {
		SimpleJdbcTemplate jt = new SimpleJdbcTemplate(dataSource);
		return jt.queryForObject(
				" select id, javaspec from StimObjData where id = ? ", 
				new ParameterizedRowMapper<StimSpecEntry> () {
					public StimSpecEntry mapRow(ResultSet rs, int rowNum)
							throws SQLException {
						StimSpecEntry ent = new StimSpecEntry();

						ent.setStimId(rs.getLong("id")); 
						ent.setSpec(rs.getString("javaspec")); 

						return ent;
					}},
				stimObjId);
	}

	public StimSpecEntry readMStickSpecFromStimObjId(long stimObjId) {
		SimpleJdbcTemplate jt = new SimpleJdbcTemplate(dataSource);
		return jt.queryForObject(
				" select id, mstickspec from StimObjData where id = ? ", 
				new ParameterizedRowMapper<StimSpecEntry> () {
					public StimSpecEntry mapRow(ResultSet rs, int rowNum)
							throws SQLException {
						StimSpecEntry ent = new StimSpecEntry();

						ent.setStimId(rs.getLong("id")); 
						ent.setSpec(rs.getString("mstickspec")); 

						return ent;
					}},
				stimObjId);
	}
	
	public StimSpecEntry readTexSpecFromStimObjId(long stimObjId) {
		SimpleJdbcTemplate jt = new SimpleJdbcTemplate(dataSource);
		
		return jt.queryForObject(
				" select id, texspec from StimObjData_vert where id = ? ", 
				new ParameterizedRowMapper<StimSpecEntry> () {
					public StimSpecEntry mapRow(ResultSet rs, int rowNum)
							throws SQLException {
						StimSpecEntry ent = new StimSpecEntry();

						ent.setStimId(rs.getLong("id")); 
						ent.setSpec(rs.getString("texspec")); 

						return ent;
					}},
				stimObjId);
	}
	
	public StimSpecEntry readTexFaceSpecFromStimObjId(long stimObjId) {
		SimpleJdbcTemplate jt = new SimpleJdbcTemplate(dataSource);
		return jt.queryForObject(
				" select id, texfacespec from StimObjData_vert where id = ? ", 
				new ParameterizedRowMapper<StimSpecEntry> () {
					public StimSpecEntry mapRow(ResultSet rs, int rowNum)
							throws SQLException {
						StimSpecEntry ent = new StimSpecEntry();

						ent.setStimId(rs.getLong("id")); 
						ent.setSpec(rs.getString("texfacespec")); 

						return ent;
					}},
				stimObjId);
	}
	
	
	public StimSpecEntry readStimDataFromStimObjId(long stimObjId) {
		SimpleJdbcTemplate jt = new SimpleJdbcTemplate(dataSource);
		return jt.queryForObject(
				" select id, dataspec from StimObjData where id = ? ", 
				new ParameterizedRowMapper<StimSpecEntry> () {
					public StimSpecEntry mapRow(ResultSet rs, int rowNum)
							throws SQLException {
						StimSpecEntry ent = new StimSpecEntry();

						ent.setStimId(rs.getLong("id")); 
						ent.setSpec(rs.getString("dataspec")); 

						return ent;
					}},
				stimObjId);
	}
	
	public long readStimObjIdFromDescriptiveId(String descriptiveId) {
			SimpleJdbcTemplate jt = new SimpleJdbcTemplate(dataSource);
			return jt.queryForLong("SELECT id from StimObjData where descId = ?", new Object[] { new String(descriptiveId) });
		}
	
	public String readDescriptiveIdFromStimObjId(long stimObjId) {
		SimpleJdbcTemplate jt = new SimpleJdbcTemplate(dataSource);
		return jt.queryForObject("SELECT descId from StimObjData where id = ?",String.class, stimObjId);
	}
	
	public String readCurrentDescriptivePrefix() {
			JdbcTemplate jt = new JdbcTemplate(dataSource);
			long tstamp = jt.queryForLong("SELECT max(tstamp) FROM DescriptiveInfo");
			int gaRun = jt.queryForInt("SELECT gaRun FROM DescriptiveInfo WHERE tstamp = ? ", new Object[] { new Long(tstamp) });
			Long cEI = jt.queryForLong("SELECT currentExptPrefix FROM DescriptiveInfo WHERE tstamp = ? ", new Object[] { new Long(tstamp) });
			
			return new String(cEI.toString() + "_r-" + gaRun);
	}
	
	public String readCurrentDescriptivePrefixAndGen() {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		long tstamp = jt.queryForLong("SELECT max(tstamp) FROM DescriptiveInfo");
		int gaRun = jt.queryForInt("SELECT gaRun FROM DescriptiveInfo WHERE tstamp = ? ", new Object[] { new Long(tstamp) });
		Long cEI = jt.queryForLong("SELECT currentExptPrefix FROM DescriptiveInfo WHERE tstamp = ? ", new Object[] { new Long(tstamp) });
		Long genNum = jt.queryForLong("SELECT genNum FROM DescriptiveInfo WHERE tstamp = ? ", new Object[] { new Long(tstamp) });
		
		return new String(cEI.toString() + "_r-" + gaRun + "_g-" + genNum);
	}
	
	public void writeDescriptiveFirstTrial(Long id) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        long tstamp = jt.queryForLong("SELECT max(tstamp) FROM DescriptiveInfo");
        
        jt.update("update DescriptiveInfo set firstTrial = ? where tstamp = ?", 
            new Object[] { id, tstamp });
    }
    
    public void writeDescriptiveLastTrial(Long id) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        long tstamp = jt.queryForLong("SELECT max(tstamp) FROM DescriptiveInfo");
        
        jt.update("update DescriptiveInfo set lastTrial = ? where tstamp = ?", 
                new Object[] { id, tstamp });
    }
	
	public void writeRefactoredResp(long id, String did, int channel, double resp) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update("insert into AcqRefactoredResp (id, descriptiveId, channel, resp) values (?, ?, ?, ?)", 
				new Object[] { id, did, channel, resp });
	}
	
	public void writeRefactoredResp(long id, String genDescId, int channel, String resp) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update("insert into AcqRefactoredResp2 (id, descriptiveGenId, channel, resp) values (?, ?, ?, ?)", 
				new Object[] { id, genDescId, channel, resp });
	}
	
	public void updateJavaSpec(long id, String javaSpec) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update("update StimObjData set javaspec = ? where id = ?", 
				new Object[] { javaSpec, id });
	}
	
	public void writeMStickSpec(long id, String mStickSpec) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update("update StimObjData set mstickspec = ? where id = ?", 
				new Object[] { mStickSpec, id });
	}
	
	public void writeVertSpec(long id, String descId, String vertSpec, String faceSpec, String normSpec) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update("insert into StimObjData_vert (id, descId, vertSpec, faceSpec, normSpec) values (?, ?, ?, ?, ?)", 
				new Object[] { id, descId, vertSpec, faceSpec, normSpec});
	}
	
	public void writeVertSpec_update(long id, String vertSpec, String faceSpec, String normSpec) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update("update StimObjData_vert set vertSpec=?, faceSpec=?, normSpec=? where id=?", 
				new Object[] { vertSpec, faceSpec, normSpec, id });
	}
	
	public boolean containsAnimation() {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		long tstamp = jt.queryForLong("SELECT max(tstamp) FROM DescriptiveInfo");		
		return jt.queryForInt("SELECT containsAnimation FROM DescriptiveInfo WHERE tstamp = ? ", new Object[] { new Long(tstamp) }) > 0;
	}
	
//	public int isRealExpt() {
//		JdbcTemplate jt = new JdbcTemplate(dataSource);
//		long tstamp = jt.queryForLong("SELECT max(tstamp) FROM DescriptiveInfo");		
//		int iRE = jt.queryForInt("SELECT isRealExpt FROM DescriptiveInfo WHERE tstamp = ? ", new Object[] { new Long(tstamp) });
//		
//		return iRE;
//	}
	
	
	
//	// for selecting the dbUtil data source: -shs
//	public void createDbUtil() {
//		// -- for testing only
//		CreateDbDataSource dataSourceMaker = new CreateDbDataSource();
////		setDbUtil(new DbUtil(dataSourceMaker.getDataSource()));
//		setDataSource(dataSourceMaker.getDataSource());
//	}
	
}
