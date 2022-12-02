package org.xper.allen.ga;

import org.xper.Dependency;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.db.vo.GenerationTaskDoneList;
import org.xper.db.vo.TaskDoneEntry;

import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

public class MockParentSelector implements ParentSelector{
    public MockParentSelector(MultiGaDbUtil dbUtil) {
        this.dbUtil = dbUtil;
    }

    @Dependency
    private MultiGaDbUtil dbUtil;

    @Override
    public List<Long> selectParents(List<String> channels, String gaName) {
        GenerationTaskDoneList taskDoneList = dbUtil.readTaskDoneForGaAndGeneration(gaName, dbUtil.readTaskDoneMaxGenerationIdForGa(gaName));
        List<TaskDoneEntry> doneTasks = taskDoneList.getDoneTasks();
        LinkedList<Long> previousGenerationIds = new LinkedList<>();
        for(TaskDoneEntry task:doneTasks){
            previousGenerationIds.add(task.getTaskId());
        }

        return previousGenerationIds;
    }
}
