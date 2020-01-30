package org.xper.util;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

import javax.sql.DataSource;

import org.springframework.dao.DataAccessException;
import org.springframework.dao.IncorrectResultSizeDataAccessException;
import org.springframework.jdbc.core.BatchPreparedStatementSetter;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.ResultSetExtractor;
import org.springframework.jdbc.core.RowCallbackHandler;
import org.springframework.jdbc.core.simple.ParameterizedRowMapper;
import org.springframework.jdbc.core.simple.SimpleJdbcTemplate;
import org.xper.Dependency;
import org.xper.db.vo.AcqDataEntry;
import org.xper.db.vo.AcqSessionEntry;
import org.xper.db.vo.BehMsgEntry;
import org.xper.db.vo.ExpLogEntry;
import org.xper.db.vo.GenerationInfo;
import org.xper.db.vo.GenerationTaskDoneList;
import org.xper.db.vo.GenerationTaskToDoList;
import org.xper.db.vo.InternalStateVariable;
import org.xper.db.vo.RFInfoEntry;
import org.xper.db.vo.RFStimSpecEntry;
import org.xper.db.vo.StimSpecEntry;
import org.xper.db.vo.SystemVariable;
import org.xper.db.vo.TaskDoneEntry;
import org.xper.db.vo.TaskToDoEntry;
import org.xper.db.vo.XfmSpecEntry;
import org.xper.exception.DbException;
import org.xper.exception.InvalidAcqDataException;
import org.xper.exception.VariableNotFoundException;
import org.xper.experiment.ExperimentTask;

import com.mindprod.ledatastream.LEDataInputStream;
import com.mindprod.ledatastream.LEDataOutputStream;

public class DbUtil {
	@Dependency
	protected
	DataSource dataSource;

	public DbUtil() {	
	}
	
	public DbUtil(DataSource dataSource) {
		super();
		this.dataSource = dataSource;
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

	/**
	 * General purpose read function.
	 * 
	 * @param sql
	 * @param param
	 * @return List of rows. Each row is a map from field name to field value.
	 */
	public List<Map<String,Object>> readDatabaseBySqlQuery(String sql, Object... param) {
		SimpleJdbcTemplate jt = new SimpleJdbcTemplate(dataSource);
		return jt.queryForList(sql, param);
	}

	/**
	 * Get AcqData between start time and stop time.
	 * 
	 * @param startTime
	 * @param stopTime
	 * @return List of {@link AcqDataEntry}
	 * @throws IOException
	 *             If the binary format is not correct, IOException is thrown.
	 */

	public List<AcqDataEntry> readAcqData(final long startTime, final long stopTime) {
		final ArrayList<AcqDataEntry> result = new ArrayList<AcqDataEntry>();
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.query(
				" select tstamp, data " + 
				" from AcqData " + 
				" where tstamp >= ? and tstamp <= ?" + 
				" order by tstamp ", 
				new Object[] {startTime, stopTime },
				new RowCallbackHandler() {
					public void processRow(ResultSet rs) throws SQLException {
						byte[] data = rs.getBytes("data");
						int len = data.length / AcqDataEntry.size();

						ByteArrayInputStream buf = new ByteArrayInputStream(data);
						LEDataInputStream in = new LEDataInputStream(buf);

						try {
							for (int ind = 0; ind < len; ind++) {
								AcqDataEntry ent = new AcqDataEntry();

								ent.setChannel ( in.readShort());
								ent.setSampleInd ( in.readInt());
								ent.setValue ( in.readDouble());
								result.add(ent);
							}

							in.close();
						} catch (IOException e) {
							throw new InvalidAcqDataException("Error reading AcqData: " + startTime + ", " + stopTime, e);
						}
					}});
		return result;
	}

	/**
	 * Get the number of rows in AcqData table with time stamp between startTime
	 * and stopTime.
	 * 
	 * @param startTime
	 * @param stopTime
	 * @return number of the rows.
	 */

	public int readAcqDataCount(long startTime, long stopTime) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		int count = jt.queryForInt(
						" select count(*) as num_rows " +
						" from AcqData where tstamp >= ? and tstamp <= ?", 
						new Object[] {startTime, stopTime });
		return count;
	}
	
	/**
	 * Get the time stamp of the most recent AcqData record.
	 * @return
	 */
	public long readAcqDataMaxTimestamp () {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		long ts = jt.queryForLong("select max(tstamp) from AcqData");
		return ts;
	}

	/**
	 * Get AcqSessionEntry with start time between fromTimestamp and
	 * toTimestamp.
	 * 
	 * @param fromTimestamp
	 * @param toTimestamp
	 * @return List of {@link AcqSessionEntry}
	 */
	public List<AcqSessionEntry> readAcqSession(long fromTimestamp,
			long toTimestamp) {
		final ArrayList<AcqSessionEntry> result = new ArrayList<AcqSessionEntry>();
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.query(
		        " select start_time, stop_time " + 
				" from AcqSession " + 
				" where start_time >= ? and start_time <= ?" + 
				" order by start_time ", 
				new Object[] {fromTimestamp, toTimestamp},
				new RowCallbackHandler() {
					public void processRow(ResultSet rs) throws SQLException {
						AcqSessionEntry ent = new AcqSessionEntry();
						ent.setStartTime(rs.getLong("start_time")); 
						ent.setStopTime(rs.getLong("stop_time")); 
						result.add(ent);
					}});
		return result;
	}

	/**
	 * Get AcqSessionEntry which surround the time stamp.
	 * 
	 * @param tstamp
	 * @return Only one {@link AcqSessionEntry} is expected.
	 * @throws IncorrectResultSizeDataAccessException
	 *             if 0 or more than 1 entries found.
	 */

	public AcqSessionEntry readAcqSession(long tstamp) {
		SimpleJdbcTemplate jt = new SimpleJdbcTemplate(dataSource);
		return jt.queryForObject(
				" select start_time, stop_time " + 
				" from AcqSession " + 
				" where start_time <= ? and stop_time >= ?" + 
				" order by start_time ",
				new ParameterizedRowMapper<AcqSessionEntry>(){
					public AcqSessionEntry mapRow(ResultSet rs, int rowNum)
							throws SQLException {
						AcqSessionEntry ent = new AcqSessionEntry();
						ent.setStartTime(rs.getLong("start_time")); 
						ent.setStopTime(rs.getLong("stop_time")); 
						return ent;
					}},
				tstamp, tstamp);
	}

	/**
	 * Get the BehMsg with time stamp from startTime to stopTime.
	 * 
	 * @param startTime
	 * @param stopTime
	 * @return List of {@link BehMsgEntry}
	 */

	public List<BehMsgEntry> readBehMsg(long startTime, long stopTime) {
		final ArrayList<BehMsgEntry> result = new ArrayList<BehMsgEntry>();
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.query(
			" select tstamp, type, msg " + 
			" from BehMsg " + 
			" where tstamp >= ? and tstamp <= ?" + 
			" order by tstamp ", 
			new Object[] {startTime, stopTime },
			new RowCallbackHandler() {
				public void processRow(ResultSet rs) throws SQLException {
					BehMsgEntry ent = new BehMsgEntry();
					ent.setTstamp(rs.getLong("tstamp")); 
					ent.setType(rs.getString("type")); 
					ent.setMsg(rs.getString("msg")); 

					result.add(ent);
				}});
		return result;
	}

	/**
	 * Read ExpLog with time stamp between startTime and stopTime.
	 * 
	 * @param startTime
	 * @param stopTime
	 * @return List of {@link ExpLogEntry}
	 */
	public List<ExpLogEntry> readExpLog(long startTime, long stopTime) {
		final ArrayList<ExpLogEntry> result = new ArrayList<ExpLogEntry>();
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.query(
			" select tstamp, memo " + 
			" from ExpLog " + 
			" where tstamp >= ? and tstamp <= ?" + 
			" order by tstamp ", 
			new Object[] {startTime, stopTime },
			new RowCallbackHandler() {
				public void processRow(ResultSet rs) throws SQLException {
					ExpLogEntry ent = new ExpLogEntry();
					ent.setTstamp(rs.getLong("tstamp")); 
					ent.setLog(rs.getString("memo")); 

					result.add(ent);
				}});
		return result;
	}

	/**
	 * Get done tasks for the generation.
	 * 
	 * @param genId
	 * @return {@link GenerationTaskDoneList} empty if there is no done tasks
	 *         for the generation in database.
	 */

	public GenerationTaskDoneList readTaskDoneByGeneration(long genId) {
		final GenerationTaskDoneList taskDone = new GenerationTaskDoneList();
		taskDone.setGenId(genId);
		taskDone.setDoneTasks(new ArrayList<TaskDoneEntry>());

		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.query(
			" select d.tstamp as tstamp, d.task_id as task_id, d.part_done as part_done" + 
			" from TaskDone d, TaskToDo t "	+ 
			" where d.task_id = t.task_id and t.gen_id = ? " + 
			" order by d.tstamp ", 
			new Object[] { genId },
			new RowCallbackHandler() {
				public void processRow(ResultSet rs) throws SQLException {
					TaskDoneEntry ent = new TaskDoneEntry();
					ent.setTaskId(rs.getLong("task_id")); 
					ent.setTstamp(rs.getLong("tstamp")); 
					ent.setPart_done(rs.getInt("part_done"));
					taskDone.getDoneTasks().add(ent);
				}});
		return taskDone;
	}

	/**
	 * Get the TaskToDo list for generation genId.
	 * 
	 * @param genId
	 * @return {@link GenerationTaskToDoList} empty if there is no tasks defined
	 *         for the generation in database.
	 */

	public GenerationTaskToDoList readTaskToDoByGeneration(long genId) {
		final GenerationTaskToDoList genTask = new GenerationTaskToDoList();
		genTask.setTasks(new ArrayList<TaskToDoEntry>());
		genTask.setGenId(genId);

		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.query(
				" select task_id, stim_id, xfm_id, gen_id " +
				" from TaskToDo " +
				" where gen_id = ? " +
				" order by task_id", 
				new Object[] { genId },
				new RowCallbackHandler() {
					public void processRow(ResultSet rs) throws SQLException {
						TaskToDoEntry task = new TaskToDoEntry();
						task.setTaskId(rs.getLong("task_id")); 
						task.setStimId(rs.getLong("stim_id")); 
						task.setXfmId(rs.getLong("xfm_id")); 
						task.setGenId(rs.getLong("gen_id")); 
						genTask.getTasks().add(task);
					}});
		return genTask;
	}

	/**
	 * Get all experiment tasks in generation genId and whose task IDs are
	 * greater than lastDoneTaskId
	 * 
	 * @param genId
	 * @param lastDoneTaskId
	 * @return
	 */
	public LinkedList<ExperimentTask> readExperimentTasks(long genId,
			long lastDoneTaskId) {
		final LinkedList<ExperimentTask> taskToDo = new LinkedList<ExperimentTask>();
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.query(
				" select t.task_id, t.stim_id, t.xfm_id, t.gen_id, " +
						" (select spec from StimSpec s where s.id = t.stim_id ) as stim_spec, " +
						" (select spec from XfmSpec x where x.id = t.xfm_id) as xfm_spec " +
				" from TaskToDo t " +
				" where t.gen_id = ? and t.task_id > ? " +
				" order by t.task_id", 
				new Object[] { genId, lastDoneTaskId },
				new RowCallbackHandler() {
					public void processRow(ResultSet rs) throws SQLException {
						ExperimentTask task = new ExperimentTask();
						task.setGenId(rs.getLong("gen_id"));
						task.setStimId(rs.getLong("stim_id"));
						task.setStimSpec(rs.getString("stim_spec"));
						task.setTaskId(rs.getLong("task_id"));
						task.setXfmId(rs.getLong("xfm_id"));
						task.setXfmSpec(rs.getString("xfm_spec"));
						taskToDo.add(task);
					}});
		return taskToDo;
	}

	/**
	 * Get all TaskTodo in task_id order as Map for generation genId.
	 * 
	 * @param genId
	 * @return Map from task id to TaskTodoEntry.
	 */
	public Map<Long, TaskToDoEntry> readTaskToDoByGenerationAsMap(long genId) {
		final Map<Long, TaskToDoEntry> genTask = new TreeMap<Long, TaskToDoEntry>();

		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.query(
			" select task_id, stim_id, xfm_id, gen_id " +
			" from TaskToDo " +
			" where gen_id = ? " +
			" order by task_id", 
			new Object[] { genId },
			new RowCallbackHandler() {
				public void processRow(ResultSet rs) throws SQLException {
					TaskToDoEntry task = new TaskToDoEntry();
					task.setTaskId(rs.getLong("task_id")); 
					task.setStimId(rs.getLong("stim_id")); 
					task.setXfmId(rs.getLong("xfm_id")); 
					task.setGenId(rs.getLong("gen_id")); 
					genTask.put(task.getTaskId(), task);
				}});
		return genTask;
	}

	/**
	 * Get all TaskToDo in task_id order as Map from startId to stopId.
	 * 
	 * @param startId
	 * @param stopId
	 * @return
	 */
	public Map<Long, TaskToDoEntry> readTaskToDoByIdRangeAsMap(long startId,
			long stopId) {
		final Map<Long, TaskToDoEntry> genTask = new TreeMap<Long, TaskToDoEntry>();

		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.query(
			" select task_id, stim_id, xfm_id " +
			" from TaskToDo " +
			" where task_id >= ? and task_id <= ? " +
			" order by task_id", 
			new Object[] { startId, stopId },
			new RowCallbackHandler() {
				public void processRow(ResultSet rs) throws SQLException {
					TaskToDoEntry task = new TaskToDoEntry();
					task.setTaskId(rs.getLong("task_id")); 
					task.setStimId(rs.getLong("stim_id")); 
					task.setXfmId(rs.getLong("xfm_id")); 
					genTask.put(task.getTaskId(), task);
				}});
		return genTask;
	}

	/**
	 * Read internal state variable.
	 * 
	 * @param namePattern
	 * @return Map from variable name to {@link SystemVariable}. Values are
	 *         stored as String.
	 */
	public Map<String, InternalStateVariable> readInternalState(
			String namePattern) {
		final HashMap<String, InternalStateVariable> result = new HashMap<String, InternalStateVariable>();
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.query(
			" select name, arr_ind, val " +
			" from InternalState " +
			" where name like ? " +
			" order by name, arr_ind", 
			new Object[] { namePattern },
			new ResultSetExtractor(){
				public Object extractData(ResultSet rs) throws SQLException,
						DataAccessException {
					InternalStateVariable var = null;
					while (rs.next()) {
						String name = rs.getString("name"); 
						String val = rs.getString("val"); 
						if (var != null && name.equalsIgnoreCase(var.getName())) {
							var.getValues().add(val);
						} else {
							var = new InternalStateVariable();
							var.setName(name);
							var.setValues(new ArrayList<String>());
							result.put(name, var);
							var.getValues().add(val);
						}
					}
					return null;
				}});
		return result;
	}

	/**
	 * Get current generation ready in database.
	 * 
	 * @return throws exception if no <code>task_to_do_gen_ready</code>
	 *         variable defined or if the format of the string value is not
	 *         correct.
	 */

	public GenerationInfo readReadyGenerationInfo() {
		String name = "task_to_do_gen_ready"; 
		Map<String, InternalStateVariable> result = readInternalState(name);
		InternalStateVariable var = result.get(name);
		if (var == null) {
			throw new VariableNotFoundException("Internal state variable '"
					+ name + "' not found.");
		}
		String genInfoXml = var.getValue(0);

		return GenerationInfo.fromXml(genInfoXml);
	}

	/**
	 * Write ready generation in InternalState table. This is used to initialize
	 * the <code>task_to_do_gen_ready</code> variable when none is in
	 * InternalState table.
	 * 
	 * @param genId
	 * @param count
	 */

	public void writeReadyGenerationInfo(long genId, int taskCount) {
		GenerationInfo info = new GenerationInfo();
		info.setGenId(genId);
		info.setTaskCount(taskCount);

		String xml = info.toXml();

		writeInternalState("task_to_do_gen_ready", 0, xml);
	}

	/**
	 * Update <code>task_to_do_gen_ready</code> with new genId and count
	 * value.
	 * 
	 * @param genId
	 * @param count
	 */
	public void updateReadyGenerationInfo(long genId, int taskCount) {
		GenerationInfo info = new GenerationInfo();
		info.setGenId(genId);
		info.setTaskCount(taskCount);

		String xml = info.toXml();

		updateInternalState("task_to_do_gen_ready", 0, xml);
	}

	/**
	 * Read RFInfo table.
	 * 
	 * @param startTime
	 * @param stopTime
	 * @return List of {@link RFInfoEntry}
	 */
	public List<RFInfoEntry> readRFInfo(long startTime, long stopTime) {
		final ArrayList<RFInfoEntry> result = new ArrayList<RFInfoEntry>();

		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.query(
				" select tstamp, info " +
				" from RFInfo " +
				" where tstamp >= ? and tstamp <= ? " + 
				" order by tstamp ", 
				new Object[] {startTime, stopTime },
				new RowCallbackHandler() {
					public void processRow(ResultSet rs) throws SQLException {
						RFInfoEntry ent = new RFInfoEntry();
						ent.setTstamp(rs.getLong("tstamp")); 
						ent.setInfo(rs.getString("info")); 
						result.add(ent);
					}				
				});
		return result;
	}

	/**
	 * Read RFStimSpec table.
	 * 
	 * @param num
	 *            retrieve the most recent <code>num</code> records in the
	 *            table.
	 * @return List of {@link StimSpecEntry}
	 */
	public List<RFStimSpecEntry> readRFStimSpec(int num) {
		final ArrayList<RFStimSpecEntry> result = new ArrayList<RFStimSpecEntry>();

		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.query(
			" select id, spec " + 
			" from RFStimSpec " +
			" order by id desc limit " + num,
			new RowCallbackHandler() {
				public void processRow(ResultSet rs) throws SQLException {
					RFStimSpecEntry ent = new RFStimSpecEntry();
					ent.setStimId(rs.getLong("id")); 
					ent.setSpec(rs.getString("spec")); 
					result.add(ent);
				}}); 
		return result;
	}

	/**
	 * Read all StimSpec for the generation.
	 * 
	 * @param genId
	 * @return Map from stimulus id to {@link StimSpecEntry}
	 */
	public Map<Long, StimSpecEntry> readStimSpecByGeneration(long genId) {
		final HashMap<Long, StimSpecEntry> result = new HashMap<Long, StimSpecEntry>();
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.query(
			" select s.id as id, s.spec as spec " + 
			" from StimSpec s, TaskToDo d " +
			" where d.stim_id = s.id and d.gen_id = ? ", 
			new Object[] {genId },
			new RowCallbackHandler() {
				public void processRow(ResultSet rs) throws SQLException {
					StimSpecEntry ent = new StimSpecEntry();
					ent.setStimId(rs.getLong("id")); 
					ent.setSpec(rs.getString("spec")); 
					result.put(ent.getStimId(), ent);
				}});
		return result;
	}

	/**
	 * Read StimSpec given a stimulus id range.
	 * 
	 * @param startId
	 * @param stopId
	 * @return Map from stimulus id to {@link StimSpecEntry}
	 */
	public Map<Long, StimSpecEntry> readStimSpec(long startId, long stopId) {
		final HashMap<Long, StimSpecEntry> result = new HashMap<Long, StimSpecEntry>();
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.query(
			" select id, spec " + 
			" from StimSpec " +
			" where id >= ? and id <= ? ", 
			new Object[] {startId, stopId },
			new RowCallbackHandler(){
				public void processRow(ResultSet rs) throws SQLException {
					StimSpecEntry ent = new StimSpecEntry();
					ent.setStimId(rs.getLong("id")); 
					ent.setSpec(rs.getString("spec")); 
					result.put(ent.getStimId(), ent);
				}});
		return result;
	}

	/**
	 * Read particular StimSpec.
	 * 
	 * @param stimId
	 * @return {@link StimSpecEntry}
	 */
	public StimSpecEntry readStimSpec(long stimId) {
		SimpleJdbcTemplate jt = new SimpleJdbcTemplate(dataSource);
		return jt.queryForObject(
				" select id, spec from StimSpec where id = ? ", 
				new ParameterizedRowMapper<StimSpecEntry> () {
					public StimSpecEntry mapRow(ResultSet rs, int rowNum)
							throws SQLException {
						StimSpecEntry ent = new StimSpecEntry();

						ent.setStimId(rs.getLong("id")); 
						ent.setSpec(rs.getString("spec")); 

						return ent;
					}},
				stimId);
	}

	/**
	 * Read System Variable from SystemVar table.
	 * 
	 * @param namePattern
	 *            The SQL <code>like</code> pattern for selecting the system
	 *            variables. '?' and '%' can be used in the pattern. "%" meaning
	 *            select all variables.
	 * @return Map from variable name to {@link SystemVariable}. Values are
	 *         stored as String.
	 */
	public Map<String, SystemVariable> readSystemVar(String namePattern) {
		return readSystemVar(namePattern, -1);
	}

	/**
	 * Read System Variable from SystemVar table.
	 * 
	 * @param namePattern
	 *            The SQL <code>like</code> pattern for selecting the system
	 *            variables. '?' and '%' can be used in the pattern. "%" meaning
	 *            select all variables.
	 * @return Map from variable name to {@link SystemVariable}. Values are
	 *         stored as String.
	 */
	public Map<String, SystemVariable> readSystemVar(String namePattern,
			long tstamp) {
		final HashMap<String, SystemVariable> result = new HashMap<String, SystemVariable>();
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		// This query selects the highest tstamp as tstamp, then for val, it
		// prepends the tstamp to the value, selects the max, then
		// removes this tstamp... The effect of these two operations is to make
		// all entries for the same name/arr_index have the same
		// tstamp and value, those of the most recent in the database.
		jt.query(
			" select name, arr_ind, max(tstamp) as tstamp, " +
					" substring(max(concat(lpad(tstamp, 32, '0'), val)), 33) as val " + 
			" from SystemVar "	+ 
			" where name like ? " + ((tstamp > 0) ? " and (tstamp < ?) " : "") + 
			" group by name, arr_ind " + 
			" order by name, arr_ind ", 
			((tstamp > 0) ? new Object[] { namePattern, tstamp } : new Object[] { namePattern }), 
			new ResultSetExtractor(){
				public Object extractData(ResultSet rs)
						throws SQLException, DataAccessException {				
					SystemVariable var = null;
					while (rs.next()) {
						String name = rs.getString("name");
						String val = rs.getString("val");
						if (var != null && name.equalsIgnoreCase(var.getName())) {
							var.getValues().add(val);
						} else {
							var = new SystemVariable();
							var.setName(name);
							var.setValues(new ArrayList<String>());
							result.put(name, var);
							var.getValues().add(val);
						}
					}
					return result;
				}});
		return result;
	}

	/**
	 * Read TaskDone table given a task ID range.
	 * 
	 * @param startId
	 * @param stopId
	 * @return List of {@link TaskDoneEntry}
	 */
	public List<TaskDoneEntry> readTaskDoneByIdRange(long startId, long stopId) {
		final ArrayList<TaskDoneEntry> result = new ArrayList<TaskDoneEntry>();
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.query(
			" select tstamp, task_id, part_done " +
			" from TaskDone " +
			" where task_id >= ? and task_id <= ?", 
			new Object[] { startId, stopId },
			new RowCallbackHandler() {
				public void processRow(ResultSet rs) throws SQLException {
					TaskDoneEntry ent = new TaskDoneEntry();
					ent.setTstamp(rs.getLong("tstamp")); 
					ent.setTaskId(rs.getLong("task_id")); 
					ent.setPart_done(rs.getInt("part_done"));
					result.add(ent);
				}});
		return result;
	}

	/**
	 * Read TaskDone table given a time stamp range.
	 * 
	 * @param startTime
	 * @param stopTime
	 * @return List of {@link TaskDoneEntry}
	 */
	public List<TaskDoneEntry> readTaskDoneByTimestampRange(long startTime,
			long stopTime) {
		final ArrayList<TaskDoneEntry> result = new ArrayList<TaskDoneEntry>();
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.query(
			" select tstamp, task_id, part_done " +
			" from TaskDone " +
			" where tstamp >= ? and tstamp <= ?", 
			new Object[] { startTime, stopTime },
			new RowCallbackHandler() {
				public void processRow(ResultSet rs) throws SQLException {
					TaskDoneEntry ent = new TaskDoneEntry();
					ent.setTstamp(rs.getLong("tstamp")); 
					ent.setTaskId(rs.getLong("task_id")); 
					ent.setPart_done(rs.getInt("part_done"));
					result.add(ent);
				}});
		return result;
	}

	/**
	 * Get the Max TaskDone ID.
	 * 
	 * @return ID as long
	 */

	public long readTaskDoneMaxId() {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		long maxId = jt.queryForLong("select max(task_id) as max_task_id from TaskDone"); 
		return maxId;
	}

	public long readTaskDoneCompleteMaxId() {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		long maxId = jt.queryForLong(
				" select max(task_id) as max_task_id " +
				" from TaskDone " +
				" where part_done = 0"); 
		return maxId;
	}

	/**
	 * Read max generation id in TaskDone table.
	 * 
	 * @return generation id as long
	 */
	public long readTaskDoneMaxGenerationId() {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		long maxId = jt.queryForLong(
				" select max(t.gen_id) as max_gen_id " +
				" from TaskDone d, TaskToDo t " +
				" where d.task_id = t.task_id"); 
		return maxId;
	}

	/**
	 * Get the max generation id for the completed task.
	 * 
	 * @return
	 */
	public long readTaskDoneCompleteMaxGenerationId() {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		long maxId = jt.queryForLong(
				" select max(t.gen_id) as max_gen_id " +
				" from TaskDone d, TaskToDo t " +
				" where d.task_id = t.task_id and d.part_done = 0"); 
		return maxId;
	}

	/**
	 * Read max generation id in TaskToDo table.
	 * 
	 * @return generation id as long
	 */
	public long readTaskToDoMaxGenerationId() {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		long maxId = jt.queryForLong("select max(gen_id) as max_gen_id from TaskToDo"); 
		return maxId;
	}

	/**
	 * Read max task ID in TaskToDo table.
	 * 
	 * @return task id as long
	 */
	public long readTaskToDoMaxId() {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		long maxId = jt.queryForLong("select max(task_id) as max_task_id from TaskToDo"); 
		return maxId;
	}

	/**
	 * Read max stimulus id from StimSpec table.
	 * 
	 * @return stim id as long
	 */
	public long readStimSpecMaxId() {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		long maxId = jt.queryForLong("select max(id) as max_id from StimSpec"); 
		return maxId;
	}

	/**
	 * Read xfm id from XfmSpec table.
	 * 
	 * @return xfm id as long
	 */

	public long readXfmSpecMaxId() {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		long maxId = jt.queryForLong("select max(id) as max_id from XfmSpec"); 
		return maxId;
	}

	/**
	 * Read timestamp of a task in TaskDone table.
	 * 
	 * @param taskId
	 * @return timestamp as long
	 */
	public long readTaskDoneTimestamp(long taskId) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		long tstamp = jt.queryForLong(
				"select tstamp from TaskDone where task_id = ? ", 
				new Object[] { new Long(taskId) });
		return tstamp;
	}

	/**
	 * Read all xfm spec for a generation.
	 * 
	 * @param genId
	 * @return Map from xfm id to {@link XfmSpecEntry}
	 */
	public Map<Long, XfmSpecEntry> readXfmSpecByGeneration(long genId) {
		final HashMap<Long, XfmSpecEntry> result = new HashMap<Long, XfmSpecEntry>();
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.query(
			" select s.id as id, s.spec as spec " + 
			" from XfmSpec s, TaskToDo d " +
			" where d.xfm_id = s.id and d.gen_id = ? ", 
			new Object[] { genId },
			new RowCallbackHandler() {
				public void processRow(ResultSet rs) throws SQLException {
					XfmSpecEntry ent = new XfmSpecEntry();
					ent.setXfmId(rs.getLong("id")); 
					ent.setSpec(rs.getString("spec")); 

					result.put(ent.getXfmId(), ent);
				}});
		return result;
	}

	/**
	 * Read xfm spec between an id range.
	 * 
	 * @param startId
	 * @param stopId
	 * @return Map from xfm id to {@link XfmSpecEntry}
	 */
	public Map<Long, XfmSpecEntry> readXfmSpec(long startId, long stopId) {
		final HashMap<Long, XfmSpecEntry> result = new HashMap<Long, XfmSpecEntry>();
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.query(
			" select id, spec " + 
			" from XfmSpec " +
			" where id >= ? and id <= ? ", 
			new Object[] { startId, stopId },
			new RowCallbackHandler() {
				public void processRow(ResultSet rs) throws SQLException {
					XfmSpecEntry ent = new XfmSpecEntry();
					ent.setXfmId(rs.getLong("id")); 
					ent.setSpec(rs.getString("spec")); 

					result.put(ent.getXfmId(), ent);
				}});
		return result;
	}

	/**
	 * Read a particular Xfm spec.
	 * 
	 * @param xfmId
	 * @return {@link XfmSpecEntry}
	 */
	public XfmSpecEntry readXfmSpec(long xfmId) {
		SimpleJdbcTemplate jt = new SimpleJdbcTemplate(dataSource);
		return jt.queryForObject(
				" select id, spec from XfmSpec where id = ? ",
				new ParameterizedRowMapper<XfmSpecEntry>() {
					public XfmSpecEntry mapRow(ResultSet rs, int rowNum)
							throws SQLException {
						XfmSpecEntry ent = new XfmSpecEntry();
						ent.setXfmId(rs.getLong("id")); 
						ent.setSpec(rs.getString("spec")); 

						return ent;
					}},
				xfmId);
	}

	/**
	 * Write AcqData record as little endian binary into database.
	 * 
	 * @param tstamp
	 * @param data
	 */

	public void writeAcqData(long tstamp, List<AcqDataEntry> data) {
		ByteArrayOutputStream buf = new ByteArrayOutputStream();
		LEDataOutputStream out = new LEDataOutputStream(buf);
		try {
			for (AcqDataEntry ent : data) {
				out.writeShort(ent.getChannel());
				out.writeInt(ent.getSampleInd());
				out.writeDouble(ent.getValue());
			}
			out.flush();
			out.close();
		} catch (IOException e) {
			throw new DbException("writeAcqData: ", e);
		}

		writeAcqData(tstamp, buf.toByteArray());
	}

	public void writeAcqData(long tstamp, byte[] data) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update("insert into AcqData (tstamp, data) values (?, ?)", 
				new Object[] {tstamp, data });
	}

	/**
	 * Repair the database if experiment program crashes and thus leaving the
	 * database in inconsistent state.
	 * 
	 * Find the AcqSession with stop_time equals Long.MAX_VALUE. Change it to
	 * current timestamp.
	 * 
	 */

	public void repairAcqSession(long tstamp) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update("update AcqSession set stop_time = ? where stop_time = ?", 
				new Object[] {tstamp, Long.MAX_VALUE });
	}

	/**
	 * Start a new AcqSession.
	 * 
	 * Stop timestamp is Long.MAX_VALUE. It will be changed to the actual value
	 * when the acq session ends.
	 * 
	 * @param startTime
	 */

	public void writeBeginAcqSession(long startTime) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update("insert into AcqSession (start_time, stop_time) values (?,?)", 
				new Object[] { startTime, Long.MAX_VALUE });
	}

	/**
	 * Write system messages.
	 * 
	 * @param tstamp
	 * @param type
	 * @param msg
	 */

	public void writeBehMsg(long tstamp, String type, String msg) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update("insert into BehMsg (tstamp, type, msg) values (?, ?, ?)", 
				new Object[] {tstamp, type, msg });
	}

	/**
	 * Write all the Behavioral messages in the array.
	 * 
	 * @param msgs
	 */
	public void writeBehMsgBatch(final BehMsgEntry[] msgs) {
		writeBehMsgBatch(msgs, msgs.length);
	}

	/**
	 * Only the first "size" elements of the array are valid, and therefore saved to database.
	 * 
	 * @param msgs
	 * @param size
	 */
	public void writeBehMsgBatch(final BehMsgEntry[] msgs, final int size) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.batchUpdate("insert into BehMsg (tstamp, type, msg) values (?, ?, ?)", 
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
	 * Write all the Behavioral messages in the array.
	 * 
	 * @param msgs
	 */
	public void writeBehMsgBatch(final ArrayList<BehMsgEntry> msgs) {
		ArrayList<BehMsgEntry> msgsNonEye = new ArrayList<BehMsgEntry>();
		ArrayList<BehMsgEntry> msgsEye = new ArrayList<BehMsgEntry>();
		
		for (int i=0; i<msgs.size(); i++) {
			if (msgs.get(i).getType().equalsIgnoreCase("EyeDeviceMessage") ||
					msgs.get(i).getType().equalsIgnoreCase("EyeWindowMessage") ||
					msgs.get(i).getType().equalsIgnoreCase("EyeZeroMessage")) {
				msgsEye.add(msgs.get(i));
			} else {
				msgsNonEye.add(msgs.get(i));
			}

		}
		
		if (msgsNonEye.size() != 0) {
			BehMsgEntry[] arr = new BehMsgEntry[msgsNonEye.size()];
			msgsNonEye.toArray(arr);
			writeBehMsgBatch(arr, msgsNonEye.size());
		}
		
		if (msgsEye.size() != 0) {
			BehMsgEntry[] arrEye = new BehMsgEntry[msgsEye.size()];
			msgsEye.toArray(arrEye);
			writeBehMsgBatchEye(arrEye, msgsEye.size());
		}
	}
	
	/**
	 * Only the first "size" elements of the array are valid, and therefore saved to database.
	 * 
	 * @param msgs
	 * @param size
	 */
	public void writeBehMsgBatchEye(final BehMsgEntry[] msgs, final int size) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.batchUpdate("insert into BehMsgEye (tstamp, type, msg) values (?, ?, ?)", 
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
	 * Write experiment log message.
	 * 
	 * @param tstamp
	 * @param log
	 */

	public void writeExpLog(long tstamp, String log) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update("insert into ExpLog(tstamp, memo) values (?, ?)", 
				new Object[] {tstamp, log });
	}

	/**
	 * End the AcqSession starts at startTime.
	 * 
	 * Write the actual stopTime.
	 * 
	 * @param startTime
	 * @param stopTime
	 */

	public void writeEndAcqSession(long startTime, long stopTime) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update("update AcqSession set stop_time = ? where start_time = ?", 
				new Object[] {stopTime, startTime });
	}

	/**
	 * Create an InternalState variable.
	 * 
	 * @param name
	 * @param arr_ind
	 * @param val
	 */

	public void writeInternalState(String name, int arr_ind, String val) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update("insert into InternalState (name, arr_ind, val) values (?, ?, ?)", 
						new Object[] { name, arr_ind, val });
	}

	/**
	 * Update the value of an InternalState variable.
	 * 
	 * @param name
	 * @param arr_ind
	 * @param val
	 */

	public void updateInternalState(String name, int arr_ind, String val) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update("update InternalState set val = ? where name = ? and arr_ind = ?", 
						new Object[] { val, name, arr_ind });
	}

	/**
	 * Write RFStimSpec.spec, thumbnail.
	 * 
	 * @param tstamp
	 * @param spec
	 * @param thumbnail
	 */

	public void writeRFStimSpec(long tstamp, String spec) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update("insert into RFStimSpec (id, spec) values (?, ?)", 
				new Object[] { tstamp, spec });
	}

	/**
	 * Write the thumbnail as binary.
	 * 
	 * @param tstamp
	 * @param thumbnail
	 */
	public void writeThumbnail(long tstamp, byte[] thumbnail) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update("insert into Thumbnail (id, data) values (?, ?)", 
				new Object[] { tstamp, thumbnail });
	}

	/**
	 * Write RF info.
	 * 
	 * @param tstamp
	 * @param info
	 */

	public void writeRFInfo(long tstamp, String info) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update("insert into RFInfo (tstamp, info) values (?, ?)", 
				new Object[] { tstamp, info });
	}

	/**
	 * Write StimSpec.
	 * 
	 * @param id
	 * @param spec
	 * @param thumbnail
	 */

	public void writeStimSpec(long id, String spec) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update("insert into StimSpec (id, spec) values (?, ?)", 
				new Object[] { id, spec });
	}

	/**
	 * Write XfmSpec
	 * 
	 * @param id
	 *            xfm ID
	 * @param spec
	 */

	public void writeXfmSpec(long id, String spec) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update("insert into XfmSpec (id, spec) values (?, ?)", 
				new Object[] { id, spec });
	}

	/**
	 * Write system variable.
	 * 
	 * @param name
	 * @param arr_ind
	 * @param val
	 * @param tstamp
	 */

	public void writeSystemVar(String name, int arr_ind, String val, long tstamp) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update("insert into SystemVar (name, arr_ind, tstamp, val) values (?, ?, ?, ?)", 
						new Object[] { name, arr_ind, tstamp, val });
	}

	/**
	 * Write TaskDone entry into database.
	 * 
	 * @param tstamp
	 * @param taskId
	 */

	public void writeTaskDone(long tstamp, long taskId, int part_done) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update("insert into TaskDone (tstamp, task_id, part_done) values (?, ?, ?)", 
						new Object[] { tstamp, taskId, part_done });

	}

	/**
	 * Write a batch of TaskeDoneEntry in one SQL statement.
	 * 
	 * @param tasks
	 * @param size
	 *            could be smaller than tasks.length, in this case, only the
	 *            first size elements are valid.
	 */
	public void writeTaskDoneBatch(final TaskDoneEntry[] tasks, final int size) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.batchUpdate("insert into TaskDone (tstamp, task_id, part_done) values (?, ?, ?)", 
						new BatchPreparedStatementSetter() {
							public int getBatchSize() {
								return size;
							}

							public void setValues(PreparedStatement ps, int i)
									throws SQLException {
								ps.setLong(1, tasks[i].getTstamp());
								ps.setLong(2, tasks[i].getTaskId());
								ps.setInt(3, tasks[i].getPart_done());
							}
						});
	}

	/**
	 * Write TaskToDo table.
	 * 
	 * @param taskId
	 * @param stimId
	 * @param xfmId
	 * @param genId
	 */

	public void writeTaskToDo(long taskId, long stimId, long xfmId, long genId) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update("insert into TaskToDo(task_id, stim_id, xfm_id, gen_id) values (?, ?, ?, ?)", 
						new Object[] { taskId, stimId, xfmId, genId });
	}

	/**
	 * Get the StimSpec for Tasks in the to do list.
	 * @param taskId
	 * @return
	 */
	public StimSpecEntry getSpecByTaskId(long taskId) {
		SimpleJdbcTemplate jt = new SimpleJdbcTemplate(dataSource);
		return jt.queryForObject(
				" select s.id as id, s.spec as spec" + 
				" from StimSpec s, TaskToDo t" + 
				" where s.id = t.stim_id and t.task_id = ?",
				new ParameterizedRowMapper<StimSpecEntry>() {
					public StimSpecEntry mapRow(ResultSet rs, int rowNum)
							throws SQLException {
						StimSpecEntry ent = new StimSpecEntry();

						ent.setStimId(rs.getLong("id")); 
						ent.setSpec(rs.getString("spec")); 

						return ent;
					}},
				new Object[] { taskId });
	}
	
}
