package org.xper.allen.util;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.LinkedList;
import java.util.Random;

import javax.sql.DataSource;

import org.xper.util.DbUtil;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowCallbackHandler;
import org.springframework.jdbc.core.simple.ParameterizedRowMapper;
import org.springframework.jdbc.core.simple.SimpleJdbcTemplate;
import org.xper.allen.db.vo.EStimObjDataEntry;
import org.xper.allen.db.vo.StimSpecEntryUtil;
import org.xper.allen.experiment.saccade.SaccadeExperimentTask;
import org.xper.allen.specs.BlockSpec;
import org.xper.allen.specs.EStimObjData;
import org.xper.allen.specs.StimSpecSpec;
import org.xper.db.vo.StimSpecEntry;
import org.xper.experiment.ExperimentTask;

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
	
	
	
	public DataSource getDataSource() {
		return dataSource;
	}

	
	//=====================EStimObjData========================================
	public void writeEStimObjData(long id, EStimObjData e) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update(
				"insert into EStimObjData (id, chans, post_trigger_delay, trig_src, num_pulses, pulse_train_period, post_stim_refractory_period, stim_shape, stim_polarity, d1, d2, dp, a1, a2, pre_stim_amp_settle, post_stim_amp_settle, maintain_amp_settle_during_pulse_train, post_stim_charge_recovery_on, post_stim_charge_recovery_off) values (?, ?, ?, ? ,? ,? ,? ,? ,? ,? ,?, ?, ?, ?, ?, ?, ?, ?)",
				new Object[] { id, e.getChans(), e.getPost_trigger_delay(), e.getTrig_src(), e.getNum_pulses(),
						e.getPulse_train_period(), e.getPost_stim_refractory_period(), e.getStim_shape(),
						e.getStim_polarity(), e.getD1(), e.getD2(), e.getDp(), e.getA1(), e.getA2(),
						e.getPre_stim_amp_settle(), e.getPost_stim_amp_settle(),
						e.getMaintain_amp_settle_during_pulse_train(), e.getPost_stim_charge_recovery_on(),
						e.getPost_stim_charge_recovery_off() });
	}
	
	public EStimObjDataEntry readEStimObjData(long estimId) {
		SimpleJdbcTemplate jt = new SimpleJdbcTemplate(dataSource);
		return jt.queryForObject(
				" select id, post_trigger_delay, trig_src, num_pulses, pulse_train_period, post_stim_refractory_period, stim_shape, stim_polarity, d1, d2, dp, a1, a2, pre_stimp_amp_settle, post_stim_amp_settle, maintain_amp_settle_during_pulse_train, post_stim_charge_recovery_on, post_stim_charge_recovery_off from EStimObjData where id = ? ",
				new ParameterizedRowMapper<EStimObjDataEntry>() {
					public EStimObjDataEntry mapRow(ResultSet rs, int rowNum) throws SQLException {
						EStimObjDataEntry e = new EStimObjDataEntry();
						e.set_id(rs.getLong("id"));
						e.setChans(rs.getString("chans"));
						e.set_post_trigger_delay(rs.getInt("post_trigger_delay"));
						e.set_trig_src(rs.getString("trig_src"));
						e.set_num_pulses(rs.getInt("num_pulses"));
						e.set_pulse_train_period(rs.getFloat("train_period"));
						e.set_post_stim_refractory_period(rs.getFloat("post_stim_refractory_period"));
						e.set_stim_shape(rs.getString("stim_shape"));
						e.set_stim_polarity(rs.getString("stim_polarity"));
						e.set_d1(rs.getFloat("d1"));
						e.set_d2(rs.getFloat("d2"));
						e.set_dp(rs.getFloat("dp"));
						e.set_a1(rs.getFloat("a1"));
						e.set_a2(rs.getFloat("a2"));
						e.set_pre_stim_amp_settle(rs.getFloat("pre_stim_amp_settle"));
						e.set_post_stim_amp_settle(rs.getFloat("post_stim_amp_settle"));
						e.set_maintain_amp_settle_during_pulse_train(
								rs.getInt("maintain_amp_settle_during_pulse_train"));
						e.set_post_stim_charge_recovery_on(rs.getFloat("post_stim_charge_recovery_on"));
						e.set_post_stim_charge_recovery_off(rs.getFloat("post_stim_charge_recovery_off"));
						return e;
					}
				}, estimId);
	}
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
		StimSpecEntry sse;
		//AC
		//System.out.println(Long.toString(lastDoneTaskId));
		if (lastDoneTaskId > 0) {
			 sse = readStimSpec(lastDoneTaskId);
		
		}
		else {
			long TaskToDoMaxId = readTaskToDoMaxId();
			 sse = readStimSpec(TaskToDoMaxId);
		}
		StimSpecEntryUtil sseU = new StimSpecEntryUtil(sse);
		
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
						SaccadeExperimentTask task = new SaccadeExperimentTask();
						task.setGenId(rs.getLong("gen_id"));
						//Serializing StimSpec
						sse.setSpec(rs.getString("stim_spec"));	
						StimSpecSpec ss = sseU.fromXmlSpec();
						//StimObjData	
						task.setStimId(readStimObjData(ss.getStimObjData()[0]).getStimId());
						task.setStimSpec(readStimObjData(ss.getStimObjData()[0]).getSpec());	
						//StimSpec
						task.setTargetEyeWinCoords(ss.getTargetEyeWinCoords());
						task.setTargetEyeWinSize(ss.getTargetEyeWinSize());
						task.setDuration(ss.getDuration());
						//TODO: EStimObjData
						task.setTaskId(rs.getLong("task_id"));
						task.setXfmId(rs.getLong("xfm_id"));
						task.setXfmSpec(rs.getString("xfm_spec"));
						taskToDo.add(task);
					}});
		return taskToDo;
	}	
}
