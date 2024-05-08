package org.xper.allen.ga;

import org.xper.Dependency;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.experiment.DatabaseTaskDataSource;
import org.xper.experiment.DatabaseTaskDataSource.UngetPolicy;
import org.xper.experiment.ExperimentTask;
import org.xper.experiment.TaskDataSource;
import org.xper.util.ThreadHelper;

import java.util.*;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.BiConsumer;

/**
 * Supports adding tasks by GA name (i.e lineage) or genId and will shuffle new tasks into current
 * task list.
 */
public class MultiGATaskDataSource extends DatabaseTaskDataSource {

    protected  static final int DEFAULT_QUERY_INTERVAL = 10;

    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    List<String> gaNames;

    @Dependency
    UngetPolicy ungetPolicy;

    @Dependency
    protected  long queryInterval = DEFAULT_QUERY_INTERVAL;


    AtomicReference<LinkedList<MultiGAExperimentTask>> currentGeneration = new AtomicReference<>();

    ThreadHelper threadHelper = new ThreadHelper("MultiGATaskDataSource", this);
    private long lastDoneTaskId = -1;


    private LinkedHashMap<String, Long> currentGenIdsForGAs = new LinkedHashMap<>();

    public boolean isRunning() {
        return threadHelper.isRunning();
    }

    @Override
    public void run() {
        try{
            if (currentGeneration.get() == null){
                currentGeneration.set(new LinkedList<>());
            }

            threadHelper.started();
            initEachGA();
            mainLoop();
        }
        finally{
            try {
                threadHelper.stopped();
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    private void initEachGA() {
        for (String ga:gaNames) {
            currentGenIdsForGAs.put(ga, -1L);
        }
    }

    private void sleepForQueryInterval() {
        try {
//            System.out.println("Query");
            Thread.sleep(queryInterval);
        } catch (InterruptedException e) {
        }
    }

    private void mainLoop() {
        while (!threadHelper.isDone()) {
            if (lastDoneTaskId < 0) {
                lastDoneTaskId = dbUtil.readTaskDoneCompleteMaxId();
            }
            MultiGaGenerationInfo readyGenerationsInfo = dbUtil.readReadyGAsAndGenerationsInfo();
            try {
                updateEachGA(readyGenerationsInfo);
            } catch (Exception e){
                e.printStackTrace();
            }
            sleepForQueryInterval();
        }
    }

    private void updateEachGA(MultiGaGenerationInfo readyGenerationsInfo) {
        readyGenerationsInfo.getGenIdForGA().forEach(new BiConsumer<String, Long>() {
            @Override
            public void accept(String readyGaName, Long readyGenId) {
                System.out.println("Checking for new tasks for " + readyGaName + " with genId " + readyGenId);
                System.out.println("Current genId for " + readyGaName + " is " + currentGenIdsForGAs.get(readyGaName));
                if (currentGenIdsForGAs.get(readyGaName) < readyGenId) {
                    System.out.println("IF STATEMENT REACHED");
                    LinkedList<MultiGAExperimentTask> newTasks = (LinkedList<MultiGAExperimentTask>) dbUtil
                            .readExperimentTasks(readyGaName, readyGenId, lastDoneTaskId);
                    System.out.println("New tasks size: " + newTasks.size());
                    if (newTasks.size() > 0) {
                        updateTasks(newTasks);
                        currentGenIdsForGAs.replace(readyGaName, readyGenId);
                    }
                }
            }
        });
    }

    private void updateTasks(LinkedList<MultiGAExperimentTask> newTasks) {
        System.err.println("updateTasks called");
        currentGeneration.get().addAll(newTasks);
//        Collections.shuffle(currentGeneration.get());

    }

    public MultiGAExperimentTask getNextTask() {
        try {
            LinkedList<MultiGAExperimentTask> tasks = currentGeneration.get();
            if (tasks == null) {
                return null;
            }
            System.out.println(tasks.size());
            MultiGAExperimentTask task = tasks.removeFirst();
            return task;
        } catch (NoSuchElementException e) {
            return null;
        }
    }

    @Override
    public void ungetTask(ExperimentTask t) {
        if (!(t instanceof MultiGAExperimentTask)) {
            throw new IllegalArgumentException("Task must be of type MultiGAExperimentTask");
        }
        MultiGAExperimentTask task = (MultiGAExperimentTask) t;

        if (logger.isDebugEnabled()) {
            logger.debug("Unget -- GA: " + task.gaName + " Generation: " + task.getGenId() + " task: " + task.getTaskId());
        }

        LinkedList<MultiGAExperimentTask> tasks = currentGeneration.get();
        if (tasks == null) {
            tasks = new LinkedList<>();
            currentGeneration.set(tasks);
        }

        // Unget behavior logic based on the configured ungetPolicy
        switch (ungetPolicy) {
            case HEAD:
                tasks.addFirst(task);
                break;
            case TAIL:
                tasks.addLast(task);
                break;
            case RAND:
                int numTasks = tasks.size();
                if (numTasks > 0) {
                    int randIndex = new Random().nextInt(numTasks);
                    tasks.add(randIndex, task);
                } else {
                    tasks.add(task);
                }
                break;
        }
    }

    public void start() {
        threadHelper.start();
    }

    public void stop() {
        if (isRunning()) {
            threadHelper.stop();
            threadHelper.join();
        }
    }

    public List<String> getGaNames() {
        return gaNames;
    }

    public void setGaNames(List<String> gaNames) {
        this.gaNames = gaNames;
    }

    public UngetPolicy getUngetPolicy() {
        return ungetPolicy;
    }

    public void setUngetPolicy(UngetPolicy ungetPolicy) {
        this.ungetPolicy = ungetPolicy;
    }

    public MultiGaDbUtil getDbUtil() {
        return dbUtil;
    }

    public void setDbUtil(MultiGaDbUtil dbUtil) {
        this.dbUtil = dbUtil;
    }

    public long getQueryInterval() {
        return queryInterval;
    }

    public void setQueryInterval(long queryInterval) {
        this.queryInterval = queryInterval;
    }
}