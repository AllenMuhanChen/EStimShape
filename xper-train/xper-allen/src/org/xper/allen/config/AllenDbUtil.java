package org.xper.allen.config;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.LinkedList;

import javax.sql.DataSource;

import org.xper.util.DbUtil;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowCallbackHandler;
import org.springframework.jdbc.core.simple.ParameterizedRowMapper;
import org.springframework.jdbc.core.simple.SimpleJdbcTemplate;
import org.xper.Dependency;
import org.xper.allen.db.vo.EStimObjDataEntry;
import org.xper.allen.specs.BlockSpec;
import org.xper.allen.specs.EStimObjData;
import org.xper.allen.specs.StimObjData;
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
	//=====================EStimObjData========================================
	public void writeEStimObjData(long id, EStimObjData e) {
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.update(
				"insert into EStimObjData (id, chan, trig_src, num_pulses, pulse_train_period, post_stim_refractory_period, stim_shape, stim_polarity, d1, d2, dp, a1, a2, pre_stim_amp_settle, post_stim_amp_settle, maintain_amp_settle_during_pulse_train, post_stim_charge_recovery_on, post_stim_charge_recovery_off) values (?, ?, ?, ? ,? ,? ,? ,? ,? ,? ,?, ?, ?, ?, ?, ?, ?, ?)",
				new Object[] { id, e.get_chan(), e.get_trig_src(), e.get_num_pulses(),
						e.get_pulse_train_period(), e.get_post_stim_refractory_period(), e.get_stim_shape(),
						e.get_stim_polarity(), e.get_d1(), e.get_d2(), e.get_dp(), e.get_a1(), e.get_a2(),
						e.get_pre_stim_amp_settle(), e.get_post_stim_amp_settle(),
						e.get_maintain_amp_settle_during_pulse_train(), e.get_post_stim_charge_recovery_on(),
						e.get_post_stim_charge_recovery_off() });
	}
	
	public EStimObjDataEntry readEStimObjData(long estimId) {
		SimpleJdbcTemplate jt = new SimpleJdbcTemplate(dataSource);
		return jt.queryForObject(
				" select id, chan, trig_src, num_pulses, pulse_train_period, post_stim_refractory_period, stim_shape, stim_polarity, d1, d2, dp, a1, a2, pre_stimp_amp_settle, post_stim_amp_settle, maintain_amp_settle_during_pulse_train, post_stim_charge_recovery_on, post_stim_charge_recovery_off from EStimObjData where id = ? ",
				new ParameterizedRowMapper<EStimObjDataEntry>() {
					public EStimObjDataEntry mapRow(ResultSet rs, int rowNum) throws SQLException {
						EStimObjDataEntry e = new EStimObjDataEntry();
						e.set_id(rs.getLong("id"));
						e.set_chan(rs.getInt("chan"));
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
	public StimObjData readStimObjData(long StimObjId) {
		SimpleJdbcTemplate jt = new SimpleJdbcTemplate(dataSource);
		return jt.queryForObject(
				" select id, spec, data from StimObjData where id = ? ",
				new ParameterizedRowMapper<StimObjData>() {
					public StimObjData mapRow(ResultSet rs, int rowNum) throws SQLException {
						StimObjData so = new StimObjData();
						so.set_id(rs.getLong("id"));
						so.set_spec(rs.getString("spec"));
						so.set_data(rs.getString("data"));
						return so;
					}
				}, StimObjId);
	}
//=================readExperimentTasks============================================
	public LinkedList<ExperimentTask> readExperimentTasks(long genId,
			long lastDoneTaskId) {
		final LinkedList<ExperimentTask> taskToDo = new LinkedList<ExperimentTask>();
		JdbcTemplate jt = new JdbcTemplate(dataSource);
		jt.query(
				" select t.task_id, t.stim_id, t.xfm_id, t.gen_id, " +
						" (select spec from StimObjData s where s.id = t.stim_id ) as stim_spec, " +
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
