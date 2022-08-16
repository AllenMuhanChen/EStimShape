package org.xper.sach.expt;

import org.xper.Dependency;
import org.xper.db.vo.GenerationInfo;
import org.xper.experiment.DatabaseTaskDataSource;
import org.xper.experiment.ExperimentTask;
import org.xper.sach.util.SachDbUtil;
import org.xper.sach.vo.SachGenerationInfo;

import java.util.LinkedList;

/**
 * Made by Allen Chen to reconcile differences between Sach's base xper and mine
 */
public class SachDatabaseTaskDataSource extends DatabaseTaskDataSource {

    @Dependency
    protected SachDbUtil dbUtil;

    public void run() {
        try {
            threadHelper.started();

            while (!threadHelper.isDone()) {
                if (lastDoneTaskId < 0) {
                    lastDoneTaskId = dbUtil.readTaskDoneCompleteMaxId();
                }
                SachGenerationInfo info = (SachGenerationInfo) dbUtil.readReadyGenerationInfo();
                if (info.getGenId() > currentGenId) {
                    // new generation found
                    LinkedList<ExperimentTask> taskToDo = dbUtil
                            .readExperimentTasks(info.getGenId(), lastDoneTaskId);

                    if (logger.isDebugEnabled()) {
                        logger.debug("Generation " + info.getGenId() + " size: "
                                + taskToDo.size());
                    }
                    if (taskToDo.size() > 0) {
                        currentGeneration.set(taskToDo);
                        currentGenId = info.getGenId();
                    }
                }
                try {
                    Thread.sleep(queryInterval);
                } catch (InterruptedException e) {
                }
            }
        } finally {
            try {
                threadHelper.stopped();
            } catch (Exception e) {
                logger.warn(e.getMessage());
                e.printStackTrace();
            }
        }
    }
}
