package org.xper.allen.util;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.HashMap;
import java.util.LinkedList;
import java.util.Map;

import javax.sql.DataSource;

import org.xper.util.DbUtil;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowCallbackHandler;
import org.springframework.jdbc.core.simple.ParameterizedRowMapper;
import org.springframework.jdbc.core.simple.SimpleJdbcTemplate;
import org.xper.allen.nafc.experiment.NAFCExperimentTask;
import org.xper.allen.saccade.SaccadeExperimentTask;
import org.xper.allen.saccade.db.vo.EStimObjDataEntry;
import org.xper.allen.saccade.db.vo.StimSpecEntryUtil;
import org.xper.allen.specs.BlockSpec;
import org.xper.allen.specs.SaccadeStimSpecSpec;
import org.xper.allen.specs.NAFCStimSpecSpec;
import org.xper.db.vo.StimSpecEntry;

//AC
public class AllenDbUtil extends DbUtil {
	/*
	@Dependency
	protected
	DataSource dataSource;

	public AllenDbUtil() {
	}

	public AllenDbUtil(DataSource dataSource) {
		super();
		this.dataSource = dataSource;
	}
*/

	/**
	 * Before DbUtil can be used. DataSource must be set.
	 *
	 * See createXperDbUtil in MATLAB directory for how to create data source.
	 *
	 * @param dataSource
	 */
	/*
	public void setDataSource(DataSource dataSource) {
		this.dataSource = dataSource;
	}
	*/
	//AC


	/**
	 * Read StimSpec given a stimulus id range.
	 *
	 * @param startId
	 * @param stopId
	 * @return Map from stimulus id to {@link StimSpecEntry}
	 */
	public Map<Long, String> readStimSpecDataByIdRangeAsMap(long startId, long stopId) {
		final HashMap<Long, String> result = new HashMap<Long, String>();
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.query(
				" select id, data " +
						" from StimSpec " +
						" where id >= ? and id <= ? ",
				new Object[] {startId, stopId },
				new RowCallbackHandler(){
					public void processRow(ResultSet rs) throws SQLException {
						result.put(
								rs.getLong("id"),
								rs.getString("data"));
					}});
		return result;
	}

	public String readStimSpecDataFor(long id) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		return (String) jt.queryForObject(
				" select data " +
						" from StimSpec " +
						" where id = ? ",
				new Object[] {id},
				String.class);
	}

	/**
	 * Write StimSpec.
	 *
	 * @param id
	 * @param spec
	 */

	public void writeStimSpec(long id, String spec, String data) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update("insert into StimSpec (id, spec, data) values (?, ?, ?)",
				new Object[] { id, spec, data });
	}

	/**
	 * Update existing StimSpec row with data
	 *
	 * @param id
	 */

	public void updateStimSpecData(long id, String data) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update("UPDATE StimSpec SET data=? WHERE id=?",
				new Object[] { data, id});
	}


	public DataSource getDataSource() {
		return dataSource;
	}




//	public EStimObjDataEntry readEStimObjData(long estimId) {
//		SimpleJdbcTemplate jt = new SimpleJdbcTemplate(dataSource);
//		return jt.queryForObject(
//				" select id, chans, post_trigger_delay, trig_src, pulse_repetition, num_pulses, pulse_train_period, post_stim_refractory_period, stim_shape, stim_polarity, d1, d2, dp, a1, a2, enable_amp_settle, pre_stim_amp_settle, post_stim_amp_settle, maintain_amp_settle_during_pulse_train, enable_charge_recovery, post_stim_charge_recovery_on, post_stim_charge_recovery_off from EStimObjData where id = ? ",
//				new ParameterizedRowMapper<EStimObjDataEntry>() {
//					public EStimObjDataEntry mapRow(ResultSet rs, int rowNum) throws SQLException {
//						EStimObjDataEntry e = new EStimObjDataEntry();
//						e.setChans(rs.getString("chans"));
//						e.set_post_trigger_delay(rs.getInt("post_trigger_delay"));
//						e.set_trig_src(rs.getString("trig_src"));
//						e.setPulse_repetition(rs.getString("pulse_repetition"));
//						e.set_num_pulses(rs.getInt("num_pulses"));
//						e.set_pulse_train_period(rs.getFloat("pulse_train_period"));
//						e.set_post_stim_refractory_period(rs.getFloat("post_stim_refractory_period"));
//						e.set_stim_shape(rs.getString("stim_shape"));
//						e.set_stim_polarity(rs.getString("stim_polarity"));
//						e.set_d1(rs.getFloat("d1"));
//						e.set_d2(rs.getFloat("d2"));
//						e.set_dp(rs.getFloat("dp"));
//						e.set_a1(rs.getFloat("a1"));
//						e.set_a2(rs.getFloat("a2"));
//						e.setEnable_amp_settle(rs.getBoolean("enable_amp_settle"));
//						e.set_pre_stim_amp_settle(rs.getFloat("pre_stim_amp_settle"));
//						e.set_post_stim_amp_settle(rs.getFloat("post_stim_amp_settle"));
//						e.set_maintain_amp_settle_during_pulse_train(
//								rs.getBoolean("maintain_amp_settle_during_pulse_train"));
//						e.setEnable_charge_recovery(rs.getBoolean("enable_charge_recovery"));
//						e.set_post_stim_charge_recovery_on(rs.getFloat("post_stim_charge_recovery_on"));
//						e.set_post_stim_charge_recovery_off(rs.getFloat("post_stim_charge_recovery_off"));
//						return e;
//					}
//				}, estimId);
//	}
//========================BlockSpec=============================================
	public BlockSpec readBlockSpec(long blockId) {
		SimpleJdbcTemplate jt = new SimpleJdbcTemplate(dataSource);
		return jt.queryForObject(
				" select id, num_stims_only, num_estims_only, num_catches, num_both, shuffle from BlockSpec where id = ? ",
				new ParameterizedRowMapper<BlockSpec>() {
					public BlockSpec mapRow(ResultSet rs, int rowNum) throws SQLException {
						BlockSpec b = new BlockSpec();
						b.set_id(rs.getLong("id"));
						b.set_num_stims_only(rs.getInt("num_stims_only"));
						b.set_num_estims_only(rs.getInt("num_estims_only"));
						b.set_num_catches(rs.getInt("num_catches"));
						b.set_num_both(rs.getInt("num_both"));
						b.set_shuffle(rs.getString("shuffle"));
						return b;
					}
				}, blockId);
	}

//========================StimObjId===============================================
	public void writeStimObjData(long id, String spec, String data) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update("insert into StimObjData (id, spec, data) values (?, ?, ?)",
				new Object[] { id, spec, data });
	}
	public StimSpecEntry readStimObjData(long StimObjId) {
		SimpleJdbcTemplate jt = new SimpleJdbcTemplate(dataSource);
		return jt.queryForObject(
				" select id, spec from StimObjData where id = ? ",
				new ParameterizedRowMapper<StimSpecEntry>() {
					public StimSpecEntry mapRow(ResultSet rs, int rowNum) throws SQLException {
						StimSpecEntry so = new StimSpecEntry();
						so.setStimId(rs.getLong("id"));
						so.setSpec(rs.getString("spec"));
						return so;
					}
				}, StimObjId);
	}


	public StimSpecEntry readEStimObjData(long EStimObjId) {
		SimpleJdbcTemplate jt = new SimpleJdbcTemplate(dataSource);
		return jt.queryForObject(
				" select id, spec from EStimObjData where id = ? ",
				new ParameterizedRowMapper<StimSpecEntry>() {
					public StimSpecEntry mapRow(ResultSet rs, int rowNum) throws SQLException {
						StimSpecEntry so = new StimSpecEntry();
						so.setStimId(rs.getLong("id"));
						so.setSpec(rs.getString("spec"));
						return so;
					}
				}, EStimObjId);
	}

	public void writeEStimObjData(long id, String spec, String data) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update("insert into EStimObjData (id, spec, data) values (?, ?, ?)",
				new Object[] { id, spec, data });
	}

//=================New ReadStimSpec to pass correct Ids to readExperimentTasks

	public StimSpecEntry readStimSpec(long StimSpecId) {
		SimpleJdbcTemplate jt = new SimpleJdbcTemplate(dataSource);
		return jt.queryForObject(
				" select id, spec from StimSpec where id = ? ",
				new ParameterizedRowMapper<StimSpecEntry>() {
					public StimSpecEntry mapRow(ResultSet rs, int rowNum) throws SQLException {
						StimSpecEntry s = new StimSpecEntry();
						s.setStimId(rs.getLong("id"));
						s.setSpec(rs.getString("spec"));
						return s;
					}
				}, StimSpecId);


	}


//=================readExperimentTasks============================================
	//TODO: Add stimObjData ID and estimObjData ID to this. Make function to read.

/**
 * Reads stimSpec from TaskToDo and pulls stimulus information from StimObjData. If StimObjData is an array, it returns a random stimulus from that array.
 * @param genId
 * @param lastDoneTaskId
 * @author allenchen
 * @return
 */
	public LinkedList<SaccadeExperimentTask> readSaccadeExperimentTasks(long genId,
			long lastDoneTaskId) {
		//
		final LinkedList<SaccadeExperimentTask> taskToDo = new LinkedList<SaccadeExperimentTask>();
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
						StimSpecEntry sse;
						//AC
						//System.out.println(Long.toString(lastDoneTaskId));
						sse = readStimSpec(rs.getLong("stim_id"));
						StimSpecEntryUtil sseU = new StimSpecEntryUtil(sse);
						SaccadeExperimentTask task = new SaccadeExperimentTask();

						task.setGenId(rs.getLong("gen_id"));
						//Serializing StimSpec
						sse.setSpec(rs.getString("stim_spec"));
						SaccadeStimSpecSpec ss = sseU.saccadeStimSpecSpecFromXmlSpec();
						//StimObjData
						task.setStimId(readStimObjData(ss.getStimObjData()[0]).getStimId());
						task.setStimSpec(readStimObjData(ss.getStimObjData()[0]).getSpec());
						//StimSpec

						//TODO SET sampleSpec and choiceSpec!


						task.setTargetEyeWinCoords(ss.getTargetEyeWinCoords());
						task.setTargetEyeWinSize(ss.getTargetEyeWinSize());
						task.setDuration(ss.getDuration());
						//TODO: EStimObjData
						task.seteStimSpec(readEStimObjData(ss.geteStimObjData()[0]).getSpec());
						task.setTaskId(rs.getLong("task_id"));
						task.setXfmId(rs.getLong("xfm_id"));
						task.setXfmSpec(rs.getString("xfm_spec"));
						taskToDo.add(task);
					}});
		return taskToDo;
	}

	public LinkedList<NAFCExperimentTask> readNAFCExperimentTasks(long genId,
			long lastDoneTaskId) {


		//
		final LinkedList<NAFCExperimentTask> taskToDo = new LinkedList<NAFCExperimentTask>();
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
						StimSpecEntry sse;
						//AC
						//System.out.println(Long.toString(lastDoneTaskId));
						sse = readStimSpec(rs.getLong("stim_id"));



						StimSpecEntryUtil sseU = new StimSpecEntryUtil(sse);

						NAFCExperimentTask task = new NAFCExperimentTask();

						task.setGenId(rs.getLong("gen_id"));
						//Serializing StimSpec
						//sse.setSpec(rs.getString("stim_spec"));
						NAFCStimSpecSpec ss = sseU.NAFCStimSpecSpecFromXmlSpec();
						//StimObjData
						//task.setStimId(readStimObjData(ss.getSampleObjData()).getStimId());
						task.setSampleSpecId(ss.getSampleObjData());
						task.setChoiceSpecId(ss.getChoiceObjData());
						task.setSampleSpec(readStimObjData(ss.getSampleObjData()).getSpec());
						task.setStimSpec(sse.getSpec());
						task.setStimId(sse.getStimId());

						int n = ss.getChoiceObjData().length;
						String[] choiceSpec = new String[n];
						for (int i = 0; i < n; i++){
							choiceSpec[i] = readStimObjData(ss.getChoiceObjData()[i]).getSpec();
						}

						task.setChoiceSpec(choiceSpec);
						//StimSpec
						task.setRewardPolicy(ss.getRewardPolicy());
						task.setRewardList(ss.getRewardList());
						task.setTargetEyeWinCoords(ss.getTargetEyeWinCoords());
						task.setTargetEyeWinSize(ss.getTargetEyeWinSize());
						//TODO: EStimObjData
						try{
							task.seteStimSpec(readEStimObjData(ss.geteStimObjData()[0]).getSpec());
						} catch(Exception e){
							System.out.println("No EStimObjData Found.");
							task.seteStimSpec("");
						}
						task.setTaskId(rs.getLong("task_id"));
						task.setXfmId(rs.getLong("xfm_id"));
						task.setXfmSpec(rs.getString("xfm_spec"));
						taskToDo.add(task);
					}});
		return taskToDo;
	}

    /**
     * Write base matchstick stimulus spec ID for a given stimulus.
     * This links a stimulus to its base matchstick specification.
     *
     * @param stimId The stimulus ID
     * @param baseMStickStimSpecId The base matchstick stimulus spec ID
     */
    public void writeBaseMStickId(long stimId, long baseMStickStimSpecId) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        jt.update("insert into BaseMStickId (stim_id, base_mstick_stim_spec_id) values (?, ?)",
                new Object[] { stimId, baseMStickStimSpecId });
    }
}