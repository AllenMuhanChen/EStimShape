package org.xper.allen.util;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowCallbackHandler;
import org.xper.allen.ga.MultiGAExperimentTask;
import org.xper.allen.ga.MultiGaGenerationInfo;
import org.xper.db.vo.*;
import org.xper.exception.VariableNotFoundException;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.*;

public class MultiGaDbUtil extends AllenDbUtil {

    public static final String TASK_TO_DO_GA_AND_GEN_READY = "task_to_do_ga_and_gen_ready";

    public MultiGaGenerationInfo readMultiGAReadyGenerationInfo() {
        String name = TASK_TO_DO_GA_AND_GEN_READY;
        Map<String, InternalStateVariable> result = readInternalState(name);
        InternalStateVariable var = result.get(name);
        if (var == null) {
            throw new VariableNotFoundException("Internal state variable '"
                    + name + "' not found.");
        }
        String genInfoXml = var.getValue(0);

        return MultiGaGenerationInfo.fromXml(genInfoXml);
    }

    public void writeTaskToDo(long taskId, long stimId, long xfmId, String gaName, long genId){
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        jt.update("insert into TaskToDo(task_id, stim_id, xfm_id, gen_id, ga_name) values (?, ?, ?, ?, ?)",
                new Object[] { taskId, stimId, xfmId, genId, gaName });
    }

    public GenerationTaskToDoList readTaskToDoByGaAndGeneration(String gaName, long genId) { // TODO
        final GenerationTaskToDoList genTask = new GenerationTaskToDoList();
        genTask.setTasks(new ArrayList<TaskToDoEntry>());
        genTask.setGenId(genId);

        JdbcTemplate jt = new JdbcTemplate(dataSource);
        jt.query(
                " select task_id, stim_id, xfm_id, ga_name, gen_id " +
                        " from TaskToDo " +
                        " where gen_id = ? and ga_name = ?" +
                        " order by task_id",
                new Object[] { genId, gaName },
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

    public void writeReadyGAsAndGenerationsInfo(List<String> gaNames){
        HashMap<String, Long> genIdForGA = new HashMap<>();
        for (String ga: gaNames){
            genIdForGA.put(ga, 0L);
        }

        MultiGaGenerationInfo generationInfoToWrite = new MultiGaGenerationInfo();
        generationInfoToWrite.setGenIdForGA(genIdForGA);
        updateInternalState(TASK_TO_DO_GA_AND_GEN_READY, 0, generationInfoToWrite.toXml());
    }


    public void updateReadyGAsAndGenerationsInfo(String gaName, Long genId){
        MultiGaGenerationInfo currentGenerationInfo = readReadyGAsAndGenerationsInfo();
        currentGenerationInfo.getGenIdForGA().put(gaName, genId);

        updateInternalState(TASK_TO_DO_GA_AND_GEN_READY, 0, currentGenerationInfo.toXml());
    }

    public MultiGaGenerationInfo readReadyGAsAndGenerationsInfo(){
        MultiGaGenerationInfo info = new MultiGaGenerationInfo();
        String name = "task_to_do_ga_and_gen_ready";

        Map<String, InternalStateVariable> result = readInternalState(name);
        InternalStateVariable var = result.get(name);
        if (var == null) {
            throw new VariableNotFoundException("Internal state variable '"
                    + name + "' not found.");
        }
        String genInfoXml = var.getValue(0);

        return MultiGaGenerationInfo.fromXml(genInfoXml);
    }

    public List<MultiGAExperimentTask> readExperimentTasks(String gaName, long genId, long lastDoneTaskId){
        final LinkedList<MultiGAExperimentTask> taskToDo = new LinkedList<>();
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        jt.query(
                " select t.task_id, t.stim_id, t.xfm_id, t.gen_id, t.ga_name, " +
                        " (select spec from StimSpec s where s.id = t.stim_id ) as stim_spec, " +
                        " (select spec from XfmSpec x where x.id = t.xfm_id) as xfm_spec " +
                    " from TaskToDo t " +
                    " where t.ga_name = ? and t.gen_id = ? and t.task_id > ? " +
                    " order by t.task_id",
                new Object[] {gaName, genId, lastDoneTaskId},
                new RowCallbackHandler() {
                    public void processRow(ResultSet rs) throws SQLException {
                        MultiGAExperimentTask task = new MultiGAExperimentTask();
                        task.setGaName(rs.getString("ga_name"));
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

    public void writeInternalState(String name, int arr_ind, String val) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        jt.update("insert into InternalState (name, arr_ind, val) values (?, ?, ?)",
                new Object[] { name, arr_ind, val });
    }

    public void writeTaskDone(long tstamp, long taskId, int part_done, String gaName, long genId) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        jt.update("insert into TaskDone (tstamp, task_id, part_done, ga_name, gen_id) values (?, ?, ?, ?, ?)",
                new Object[] { tstamp, taskId, part_done, gaName, genId });

    }

    public long readTaskDoneMaxGenerationIdForGa(String gaName) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        long maxId = jt.queryForLong(
                " select max(t.gen_id) as max_gen_id " +
                        " from TaskDone d, TaskToDo t " +
                        " where d.task_id = t.task_id and t.ga_name = ?",
                new Object[]{gaName});
        return maxId;
    }

    public GenerationTaskDoneList readTaskDoneForGaAndGeneration(String gaName, long genId) {
        final GenerationTaskDoneList taskDone = new GenerationTaskDoneList();
        taskDone.setGenId(genId);
        taskDone.setDoneTasks(new ArrayList<TaskDoneEntry>());

        JdbcTemplate jt = new JdbcTemplate(dataSource);
        jt.query(
                " select d.tstamp as tstamp, d.task_id as task_id, d.part_done as part_done" +
                        " from TaskDone d, TaskToDo t "	+
                        " where d.task_id = t.task_id and t.gen_id = ? and t.ga_name = ?" +
                        " order by d.tstamp ",
                new Object[] { genId, gaName },
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


}
