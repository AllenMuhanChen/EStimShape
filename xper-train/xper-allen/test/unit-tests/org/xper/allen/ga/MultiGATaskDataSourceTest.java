package org.xper.allen.ga;

import org.junit.Test;
import org.xper.allen.util.DbUtilFactory;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.util.ThreadUtil;

import java.util.*;

import static org.junit.Assert.*;


public class MultiGATaskDataSourceTest {

    private static MultiGATaskDataSource taskDataSource;
    private static final MultiGaDbUtil dbUtil = DbUtilFactory.createGaDbUtil("allen_estimshape_dev_221110");


    private long taskId=1;

    private static void setUp() {
        List<String> GAs = new LinkedList<>();
        GAs.add("testGA1");
        GAs.add("testGA2");

        taskDataSource = new MultiGATaskDataSource();
        taskDataSource.setGaNames(GAs);
        taskDataSource.setDbUtil(dbUtil);
    }

    public static void main(String[] args) {
        setUp();
        dbUtil.writeReadyGAsAndGenerationsInfo(Arrays.asList("testGA1", "testGA2"));
        taskDataSource.start();

    }

    @Test
    public void handles_updating_generation_info_across_two_GAs(){
        setUp();
        dbUtil.writeReadyGAsAndGenerationsInfo(Arrays.asList("testGA1", "testGA2"));
        taskDataSource.start();
        sleep();

        //Gen 1
        putNewGeneration("testGA1", 0L);
        sleep();
        putNewGeneration("testGA2", 0L);

        sleep();

        MultiGAExperimentTask nextTask = taskDataSource.getNextTask();
        assertEquals(0L, nextTask.getGenId());

        nextTask = taskDataSource.getNextTask();
        assertEquals(0L, nextTask.getGenId());


        //Gen 2 - assymetric
        putNewGeneration("testGA1", 2L);
        sleep();
        nextTask = taskDataSource.getNextTask();
        assertEquals("testGA1", nextTask.getGaName());
        assertEquals(2L, nextTask.getGenId());
    }

    private void sleep() {
        ThreadUtil.sleep(500);
    }

    private void putNewGeneration(String gaName, long genId) {
        taskId = dbUtil.readTaskToDoMaxId();
        taskId++;
        dbUtil.writeTaskToDo(taskId,0,0, gaName, genId);
        dbUtil.updateReadyGAsAndGenerationsInfo(gaName, genId);
    }

    private MultiGAExperimentTask testTask(String testGA1) {
        MultiGAExperimentTask taskForGA1 = new MultiGAExperimentTask();
        taskForGA1.setGaName(testGA1);
        return taskForGA1;
    }
}