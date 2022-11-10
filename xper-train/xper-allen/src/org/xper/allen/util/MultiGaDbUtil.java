package org.xper.allen.util;

import org.xper.allen.ga.MultiGAExperimentTask;
import org.xper.allen.ga.MultiGaGenerationInfo;

import java.util.List;
import java.util.Map;

public interface MultiGaDbUtil {
    public void writeTaskToDo(long taskId, long stimId, long xfmId, String genName, long genId);

    void writeReadyGenerationInfo(List<String> gaNames);

    MultiGaGenerationInfo readReadyGenerationInfo();

    void updateReadyGenerationInfo(String gaName, Long genId);

    long readTaskDoneCompleteMaxId();

    List<MultiGAExperimentTask> readExperimentTasks(String gaName, long genId, long lastDoneTaskId);
}
