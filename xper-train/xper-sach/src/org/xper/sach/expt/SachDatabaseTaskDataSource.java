package org.xper.sach.expt;

import org.xper.Dependency;
import org.xper.experiment.DatabaseTaskDataSource;
import org.xper.experiment.ExperimentTask;
import org.xper.sach.util.SachDbUtil;
import org.xper.db.vo.MultiLineageGenerationInfo;

import java.util.LinkedList;

/**
 * Made by Allen Chen to reconcile differences between Sach's base xper and mine
 */
public class SachDatabaseTaskDataSource extends DatabaseTaskDataSource {

    public void setDbUtil(SachDbUtil dbUtil) {
        this.dbUtil = dbUtil;
    }

    @Dependency
    protected SachDbUtil dbUtil;

    public void run() {
        try {
            threadHelper.started();

            while (!threadHelper.isDone()) {
                if (lastDoneTaskId < 0) {
                    lastDoneTaskId = dbUtil.readTaskDoneCompleteMaxId();
                }
                MultiLineageGenerationInfo info = (MultiLineageGenerationInfo) dbUtil.readReadyGenerationInfo();
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
