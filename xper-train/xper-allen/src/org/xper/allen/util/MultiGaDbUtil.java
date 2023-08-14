package org.xper.allen.util;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowCallbackHandler;
import org.springframework.jdbc.core.RowMapper;
import org.xper.allen.ga.MultiGAExperimentTask;
import org.xper.allen.ga.MultiGaGenerationInfo;
import org.xper.allen.ga.StimGaInfo;
import org.xper.allen.pga.StimGaInfoEntry;
import org.xper.db.vo.*;
import org.xper.exception.VariableNotFoundException;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.*;

/**
 * Contains database operations for multi-ga experiment.
 *
 * Involves tables:
 * StimGaInfo
 * InternalState
 * TaskToDo
 * TaskDone
 */
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

    public void writeReadyGAandGenerationInfo(String gaName){
        List<String> gaNames = new ArrayList<>();
        gaNames.add(gaName);

        writeReadyGAsAndGenerationsInfo(gaNames);
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


    public void writeStimGaInfo(Long stimId, Long parentId, String gaName, Long genId, Long lineageId, String treeSpec) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        jt.update("insert into StimGaInfo (stim_id, parent_id, ga_name, gen_id, lineage_id, tree_spec) values (?, ?, ?, ?, ?, ?)",
                new Object[] {stimId, parentId, gaName, genId, lineageId, treeSpec});
    }

    public void writeStimGaInfo(Long stimId, Long parentId, String gaName, Long genId, Long lineageId, String treeSpec, String stimType) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        jt.update("insert into StimGaInfo (stim_id, parent_id, ga_name, gen_id, lineage_id, tree_spec, stim_type) values (?, ?, ?, ?, ?, ?, ?)",
                new Object[] {stimId, parentId, gaName, genId, lineageId, treeSpec, stimType});
    }

    public StimGaInfo readStimGaInfo(Long stimId) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        final StimGaInfo info = new StimGaInfo();
        jt.query(
                " select * from StimGaInfo where stim_id = ?",
                new Object[] { stimId },
                new RowCallbackHandler() {
                    public void processRow(ResultSet rs) throws SQLException {
                        info.setGenId(rs.getLong("gen_id"));
                        info.setGaName(rs.getString("ga_name"));
                        info.setParentId(rs.getLong("parent_id"));
                        info.setStimId(rs.getLong("stim_id"));
                        info.setTreeSpec(rs.getString("tree_spec"));
                        info.setLineageId(rs.getLong("lineage_id"));
                        info.setStimType(rs.getString("stim_type"));
                    }});
        return info;
    }

    public Long readParentFor(Long stimId) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        Long parentId = jt.queryForLong(
                " select parent_id from StimGaInfo where stim_id = ?",
                new Object[] { stimId });
        return parentId;
    }

    public Map<Long, List<Long>> readTaskDoneIdsForStimIds(String gaName, long genId){
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        final Map<Long, List<Long>> result = new HashMap<>();
        jt.query(
                " select t.stim_id, d.task_id " +
                        " from TaskDone d, TaskToDo t " +
                        " where d.task_id = t.task_id and t.ga_name = ? and t.gen_id = ?",
                new Object[] { gaName, genId },
                new RowCallbackHandler() {
                    public void processRow(ResultSet rs) throws SQLException {
                        Long stimId = rs.getLong("stim_id");
                        Long taskId = rs.getLong("task_id");
                        List<Long> taskIds = result.get(stimId);
                        if (taskIds == null) {
                            taskIds = new ArrayList<>();
                            result.put(stimId, taskIds);
                        }
                        taskIds.add(taskId);
                    }});
        return result;
    }

    public Map<Long, List<Long>> readTaskDoneIdsForStimIds(String gaName){
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        final Map<Long, List<Long>> result = new HashMap<>();
        jt.query(
                " select t.stim_id, d.task_id " +
                        " from TaskDone d, TaskToDo t " +
                        " where d.task_id = t.task_id and t.ga_name = ?",
                new Object[] { gaName },
                new RowCallbackHandler() {
                    public void processRow(ResultSet rs) throws SQLException {
                        Long stimId = rs.getLong("stim_id");
                        Long taskId = rs.getLong("task_id");
                        List<Long> taskIds = result.get(stimId);
                        if (taskIds == null) {
                            taskIds = new ArrayList<>();
                            result.put(stimId, taskIds);
                        }
                        taskIds.add(taskId);
                    }});
        return result;
    }

    public List<Long> readAllStimIdsForGa(String gaName){
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        final List<Long> result = new ArrayList<>();
        jt.query(
                " select distinct stim_id from StimGaInfo where ga_name = ?",
                new Object[] { gaName },
                new RowCallbackHandler() {
                    public void processRow(ResultSet rs) throws SQLException {
                        result.add(rs.getLong("stim_id"));
                    }});
        return result;
    }

    public List<Long> readAllDoneStimIdsForGa(String gaName){
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        final List<Long> result = new ArrayList<>();
        jt.query(
                " select distinct s.stim_id from StimGaInfo s, TaskDone d, TaskToDo t where (d.task_id = t.task_id) and (s.stim_id = t.stim_id) and s.ga_name = ?",
                new Object[] { gaName },
                new RowCallbackHandler() {
                    public void processRow(ResultSet rs) throws SQLException {
                        result.add(rs.getLong("stim_id"));
                    }});
        return result;
    }

    public List<Long> readDoneStimIdsFromLineage(String gaName, Long lineageId) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        final List<Long> result = new ArrayList<>();
        jt.query(
                " select distinct s.stim_id from StimGaInfo s, TaskDone d, TaskToDo t where s.ga_name = ? and s.lineage_id = ? and (d.task_id = t.task_id) and (s.stim_id = t.stim_id)",
                new Object[] { gaName, lineageId },
                new RowCallbackHandler() {
                    public void processRow(ResultSet rs) throws SQLException {
                        result.add(rs.getLong("stim_id"));
                    }});
        return result;
    }

    public List<String> readAllTreeSpecsForGa(String gaName) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        final List<String> result = new ArrayList<>();
        jt.query(
                " select distinct tree_spec from StimGaInfo where ga_name = ?",
                new Object[] { gaName },
                new RowCallbackHandler() {
                    public void processRow(ResultSet rs) throws SQLException {
                        result.add(rs.getString("tree_spec"));
                    }});
        return result;
    }

    public Integer readFirstGenId(Long lineageId) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        final Integer[] result = new Integer[1];
        jt.query(
                " select min(gen_id) as gen_id from StimGaInfo where lineage_id = ?",
                new Object[] { lineageId },
                new RowCallbackHandler() {
                    public void processRow(ResultSet rs) {
                        try {
                            result[0] = rs.getInt("gen_id");
                        } catch (SQLException e) {
                            result[0] = 0;
                        }
                    }});
        return result[0];
    }

    public Long readLineageId(Long stimId) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        final Long[] result = new Long[1];
        jt.query(
                " select lineage_id from StimGaInfo where stim_id = ?",
                new Object[] { stimId },
                new RowCallbackHandler() {
                    public void processRow(ResultSet rs) {
                        try {
                            result[0] = rs.getLong("lineage_id");
                        } catch (SQLException e) {
                            result[0] = 0L;
                        }
                    }});
        return result[0];
    }

    public Integer readLatestGenIdForLineage(Long lineageId) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        final Integer[] result = new Integer[1];
        jt.query(
                " select max(gen_id) as gen_id from StimGaInfo where lineage_id = ?",
                new Object[] { lineageId },
                new RowCallbackHandler() {
                    public void processRow(ResultSet rs) {
                        try {
                            result[0] = rs.getInt("gen_id");
                        } catch (SQLException e) {
                            result[0] = 0;
                        }
                    }});
        return result[0];
    }

    public StimGaInfoEntry readStimGaInfoEntry(long stimId) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        String sqlQuery = "SELECT parent_id, lineage_id, stim_type, response, mutation_magnitude FROM StimGaInfo WHERE stim_id = ?";
        List<StimGaInfoEntry> entries = jt.query(sqlQuery, new Object[]{stimId}, new RowMapper() {
            @Override
            public Object mapRow(ResultSet rs, int rowNum) throws SQLException {
                long parentId = rs.getLong("parent_id");
                long lineageId = rs.getLong("lineage_id");
                String stimType = rs.getString("stim_type");
                double response = rs.getDouble("response");
                Double mutationMagnitude = rs.getDouble("mutation_magnitude"); // Allows for null values
                return new StimGaInfoEntry(stimId, parentId, lineageId, stimType, response, mutationMagnitude);
            }
        });

        if (entries.isEmpty()) {
            throw new RuntimeException("Could not find StimGaInfo entry for stim_id " + stimId);
        } else {
            return entries.get(0); // Return the first (and likely only) entry
        }
    }


    public List<Long> readAllLineageIds(String gaName) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        final List<Long> result = new ArrayList<>();
        jt.query(
                " select distinct l.lineage_id from LineageGaInfo l, StimGaInfo s where s.ga_name = ? and s.lineage_id = l.lineage_id",
                new Object[] { gaName },
                new RowCallbackHandler() {
                    public void processRow(ResultSet rs) throws SQLException {
                        result.add(rs.getLong("lineage_id"));
                    }});
        return result;
    }

    public void writeResponse(Long stimId, Double response) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        jt.update("update StimGaInfo set response = ? where stim_id = ?",
                new Object[] { response, stimId });
    }

    public Integer readGenIdForStimId(Long childId) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        final Integer[] result = new Integer[1];
        jt.query(
                " select gen_id from StimGaInfo where stim_id = ?",
                new Object[] { childId },
                new RowCallbackHandler() {
                    public void processRow(ResultSet rs) {
                        try {
                            result[0] = rs.getInt("gen_id");
                        } catch (SQLException e) {
                            result[0] = 0;
                        }
                    }});
        return result[0];
    }

    public List<Long> readLineageIdsForExperiment(long experimentId) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        List<Long> lineageIds = new ArrayList<>();
        jt.query(
                "SELECT lineage_id FROM LineageGaInfo WHERE experiment_id = ?",
                new Object[]{experimentId},
                new RowCallbackHandler() {
                    @Override
                    public void processRow(ResultSet rs) throws SQLException {
                        lineageIds.add(rs.getLong("lineage_id"));
                    }
                });
        return lineageIds;
    }

    public List<Long> findStimIdsWithoutStimSpec(List<Long> lineageIdsInThisExperiment) {
        if (lineageIdsInThisExperiment == null || lineageIdsInThisExperiment.isEmpty()) {
            return Collections.emptyList(); // Return an empty list if there are no lineage IDs
        }

        String inClause = String.join(",", Collections.nCopies(lineageIdsInThisExperiment.size(), "?"));
        String sqlQuery =
                "SELECT s.stim_id " +
                        "FROM StimGaInfo s " +
                        "LEFT JOIN StimSpec ss ON s.stim_id = ss.id " +
                        "WHERE s.lineage_id IN (" + inClause + ") AND ss.id IS NULL";

        JdbcTemplate jt = new JdbcTemplate(dataSource);
        List<Long> stimIdsWithoutStimSpec = new ArrayList<>();
        jt.query(
                sqlQuery,
                lineageIdsInThisExperiment.toArray(),
                new RowCallbackHandler() {
                    @Override
                    public void processRow(ResultSet rs) throws SQLException {
                        stimIdsWithoutStimSpec.add(rs.getLong("stim_id"));
                    }
                });
        return stimIdsWithoutStimSpec;
    }


    public Long readCurrentExperimentId(String experimentName) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        List<Long> experimentIds = new ArrayList<>();
        jt.query(
                "SELECT experiment_id FROM CurrentExperiments WHERE experiment_name = ? ORDER BY experiment_id desc",
                new Object[]{experimentName},
                new RowCallbackHandler() {
                    @Override
                    public void processRow(ResultSet rs) throws SQLException {
                        experimentIds.add(rs.getLong("experiment_id"));
                    }
                });
        if (experimentIds.size() == 0) {
            throw new RuntimeException("Could not find experiment with name " + experimentName);
        } else {
            return experimentIds.get(0); // Return the first experiment ID from the result
        }
    }


    public static class LineageGaInfo {
        Long lineageId;
        String treeSpec;
        Double regimeScore;
        String lineageData;

        public LineageGaInfo() {
        }

        public LineageGaInfo(Long lineageId, String treeSpec, Double regimeScore, String lineageData) {
            this.lineageId = lineageId;
            this.treeSpec = treeSpec;
            this.regimeScore = regimeScore;
            this.lineageData = lineageData;
        }

        public LineageGaInfo(Long lineageId, String treeSpec, Double regimeScore) {
            this.lineageId = lineageId;
            this.treeSpec = treeSpec;
            this.regimeScore = regimeScore;
            this.lineageData = "";
        }
    }

    public LineageGaInfo readLineageGaInfo(long lineageId) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        LineageGaInfo lineageGaInfo = new LineageGaInfo();
        jt.query("SELECT * FROM LineageGaInfo WHERE lineageId = ?",
                new Object[]{lineageId},
                new RowCallbackHandler() {
                    @Override
                    public void processRow(ResultSet rs) throws SQLException {
                        lineageGaInfo.lineageId = rs.getLong("lineage_id");
                        lineageGaInfo.treeSpec = rs.getString("tree_spec");
                        lineageGaInfo.regimeScore = rs.getDouble("regime_score");
                        lineageGaInfo.lineageData = rs.getString("lineage_data");
                    }});
        return lineageGaInfo;
    }

    public void writeLineageGaInfo(LineageGaInfo lineageGaInfo) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        jt.update("INSERT INTO LineageGaInfo (lineage_id, tree_spec, regime_score, lineage_data) VALUES (?, ?, ?, ?)",
                new Object[] {
                        lineageGaInfo.lineageId,
                        lineageGaInfo.treeSpec,
                        lineageGaInfo.regimeScore,
                        lineageGaInfo.lineageData
                });
    }

    public Double readRegimeScore(Long lineageId) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        List<Double> regimeScore = new ArrayList<>();
        jt.query("SELECT regime_score FROM LineageGaInfo WHERE lineage_id = ?",
                new Object[]{lineageId},
                new RowCallbackHandler() {
                    @Override
                    public void processRow(ResultSet rs) throws SQLException {
                        regimeScore.add(rs.getDouble("regime_score"));
                    }});
        if (regimeScore.size() == 0) {
            throw new RuntimeException("No regime score found for lineageId " + lineageId);
        }
        else if (regimeScore.size() > 1) {
            throw new RuntimeException("Multiple regime scores found for lineageId " + lineageId);
        }
        else {
            return regimeScore.get(0);
        }
    }

    public void updateRegimeScore(Long lineageId, Double regimeScore) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        jt.update("UPDATE LineageGaInfo SET regime_score = ? WHERE lineage_id = ?",
                new Object[] {
                        regimeScore,
                        lineageId
                });
    }

    public String readLineageTreeSpec(long lineageId) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        List<String> treeSpec = new ArrayList<>();
        jt.query("SELECT tree_spec FROM LineageGaInfo WHERE lineage_id = ?",
                new Object[]{lineageId},
                new RowCallbackHandler() {
                    @Override
                    public void processRow(ResultSet rs) throws SQLException {
                        treeSpec.add(rs.getString("tree_spec"));
                    }});
        if (treeSpec.size() == 0) {
            throw new RuntimeException("No tree spec found for lineageId " + lineageId);
        }
        else if (treeSpec.size() > 1) {
            throw new RuntimeException("Multiple tree specs found for lineageId " + lineageId);
        }
        else {
            return treeSpec.get(0);
        }
    }

    public void updateLineageTreeSpec(long lineageId, String treeSpec) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        jt.update("UPDATE LineageGaInfo SET tree_spec = ? WHERE lineage_id = ?",
                new Object[] {
                        treeSpec,
                        lineageId
                });
    }

    public void writeLineageData(Long lineageId, String lineageData){
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        jt.update("INSERT INTO LineageGaInfo (lineage_id, lineage_data) VALUES (?, ?) ON DUPLICATE KEY UPDATE lineage_data = ?",
                new Object[] {
                        lineageId,
                        lineageData,
                        lineageData
                });
    }

    public String readLineageData(Long lineageId) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        List<String> lineageData = new ArrayList<>();
        jt.query("SELECT lineage_data FROM LineageGaInfo WHERE lineage_id = ?",
                new Object[]{lineageId},
                new RowCallbackHandler() {
                    @Override
                    public void processRow(ResultSet rs) throws SQLException {
                        lineageData.add(rs.getString("lineage_data"));
                    }});
        if (lineageData.size() == 0) {
            throw new RuntimeException("No lineage data found for lineageId " + lineageId);
        }
        else if (lineageData.size() > 1) {
            throw new RuntimeException("Multiple lineage data found for lineageId " + lineageId);
        }
        else {
            return lineageData.get(0);
        }
    }

    public List<Long> readStimIdsFromLineageAndType(Long lineageId, String stimType){
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        List<Long> stimIds = new ArrayList<>();
        jt.query("SELECT stim_id FROM StimGaInfo WHERE lineage_id = ? AND stim_type = ?",
                new Object[]{lineageId, stimType},
                new RowCallbackHandler() {
                    @Override
                    public void processRow(ResultSet rs) throws SQLException {
                        stimIds.add(rs.getLong("stim_id"));
                    }
                });
        return stimIds;
    }

    public Map<Integer, List<Long>> readStimIdsFromGenIdsFor(Long lineageId){
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        Map<Integer, List<Long>> stimIdsByGenId = new HashMap<>();
        jt.query("SELECT stim_id, gen_id FROM StimGaInfo WHERE lineage_id = ?",
                new Object[]{lineageId},
                new RowCallbackHandler() {
                    @Override
                    public void processRow(ResultSet rs) throws SQLException {
                        Long stimId = rs.getLong("stim_id");
                        Integer genId = rs.getInt("gen_id");
                        if (!stimIdsByGenId.containsKey(genId)) {
                            stimIdsByGenId.put(genId, new ArrayList<>());
                        }
                        stimIdsByGenId.get(genId).add(stimId);
                    }
                });
        return stimIdsByGenId;
    }

    public String readGaNameFor(Long lineageId){
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        List<String> gaNames = new ArrayList<>();
        jt.query("SELECT ga_name FROM StimGaInfo WHERE lineage_id = ?",
                new Object[]{lineageId},
                new RowCallbackHandler() {
                    @Override
                    public void processRow(ResultSet rs) throws SQLException {
                        gaNames.add(rs.getString("ga_name"));
                    }
                });
        if (gaNames.size() == 0) {
            throw new RuntimeException("No ga name found for lineageId " + lineageId);
        }
        else {
            return gaNames.get(0);
        }
    }

    public String readStimTypeFor(long stimId){
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        List<String> stimTypes = new ArrayList<>();
        jt.query("SELECT stim_type FROM StimGaInfo WHERE stim_id = ?",
                new Object[]{stimId},
                new RowCallbackHandler() {
                    @Override
                    public void processRow(ResultSet rs) throws SQLException {
                        stimTypes.add(rs.getString("stim_type"));
                    }
                });
        if (stimTypes.size() == 0) {
            throw new RuntimeException("No stim type found for stimId " + stimId);
        }
        else {
            return stimTypes.get(0);
        }
    }
}