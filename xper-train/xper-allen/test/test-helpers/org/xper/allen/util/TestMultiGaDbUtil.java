package org.xper.allen.util;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowCallbackHandler;
import org.xper.allen.ga.MultiGAExperimentTask;
import org.xper.allen.ga.MultiGaGenerationInfo;
import org.xper.db.vo.GenerationTaskDoneList;
import org.xper.db.vo.TaskDoneEntry;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.*;
import java.util.function.BiConsumer;

/**
 * swaps database operations with simple set and gets for testing purposes.
 */
public class TestMultiGaDbUtil extends MultiGaDbUtil {

    LinkedList<MultiGAExperimentTask> tasksToDo = new LinkedList<>();


    @Override
    public void writeTaskToDo(long taskId, long stimId, long xfmId, String gaName, long genId) {
        MultiGAExperimentTask task = new MultiGAExperimentTask();
        task.setTaskId(taskId);
        task.setGaName(gaName);
        task.setXfmId(xfmId);
        task.setStimId(stimId);
        task.setGenId(genId);

        tasksToDo.add(task);

    }

    Map<String, Long> genIdForGA;
    @Override
    public void writeReadyGAsAndGenerationsInfo(List<String> gaNames){
        genIdForGA = new HashMap<>();
        for (String ga: gaNames){
            genIdForGA.put(ga, 0L);
        }
    }

    @Override
    public MultiGaGenerationInfo readReadyGAsAndGenerationsInfo(){
        MultiGaGenerationInfo info = new MultiGaGenerationInfo();
        info.setGenIdForGA(genIdForGA);

        return info;
    }

    @Override
    public void updateReadyGAsAndGenerationsInfo(String gaName, Long genId) {
        genIdForGA.put(gaName, genId);
    }

    @Override
    public long readTaskDoneCompleteMaxId(){
        return 0;
    }

    @Override
    public List<MultiGAExperimentTask> readExperimentTasks(String gaName, long genId, long lastTaskDoneId){
        LinkedList<MultiGAExperimentTask> output = new LinkedList<>();
        for (MultiGAExperimentTask task:tasksToDo){
            if (task.getTaskId()>lastTaskDoneId && task.getGaName().equals(gaName) && task.getGenId() == genId){
                output.add(task);
            }
        }
        return output;
    }

    @Override
    public long readTaskDoneMaxGenerationIdForGa(String gaName) {
        return 1L;
    }

    /**
     * For mock testing IntanSpikeParentSelector, there's two done tasks, one with taskId1, the other with taskId2
     * @param gaName
     * @param genId
     * @return
     */
    @Override
    public GenerationTaskDoneList readTaskDoneForGaAndGeneration(String gaName, long genId) {
        final GenerationTaskDoneList taskDone = new GenerationTaskDoneList();
        List<TaskDoneEntry> doneTasks = new LinkedList<>();

        TaskDoneEntry entry1 = new TaskDoneEntry();
        entry1.setTaskId(12345);
        TaskDoneEntry entry2 = new TaskDoneEntry();
        entry2.setTaskId(12346);
        doneTasks.add(entry1); doneTasks.add(entry2);
        taskDone.setDoneTasks(doneTasks);

        return taskDone;
    }

}
