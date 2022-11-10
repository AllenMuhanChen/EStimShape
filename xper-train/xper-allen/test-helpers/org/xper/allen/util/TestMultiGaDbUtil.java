package org.xper.allen.util;

import org.xper.allen.ga.MultiGAExperimentTask;
import org.xper.allen.ga.MultiGaGenerationInfo;

import java.util.HashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.function.BiConsumer;

/**
 * swaps database operations with simple set and gets for testing purposes.
 */
public class TestMultiGaDbUtil implements MultiGaDbUtil {

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
    public void writeReadyGenerationInfo(List<String> gaNames){
        genIdForGA = new HashMap<>();
        for (String ga: gaNames){
            genIdForGA.put(ga, 0L);
        }
    }

    @Override
    public MultiGaGenerationInfo readReadyGenerationInfo(){
        MultiGaGenerationInfo info = new MultiGaGenerationInfo();
        info.setGenIdForGA(genIdForGA);

        return info;
    }

    @Override
    public void updateReadyGenerationInfo(String gaName, Long genId) {
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
}
