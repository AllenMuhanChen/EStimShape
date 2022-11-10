package org.xper.allen.ga;

import org.junit.Test;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.allen.util.TestMultiGaDbUtil;
import org.xper.util.ThreadUtil;

import java.util.*;

import static org.junit.Assert.*;


public class MultiGATaskDataSourceTest {

    private static MultiGATaskDataSource dataSource;
    private static MultiGaDbUtil dbUtil = new TestMultiGaDbUtil();

    private long taskId=1;

    private static void setUp() {
        List<String> GAs = new LinkedList<>();
        GAs.add("testGA1");
        GAs.add("testGA2");

        dataSource = new MultiGATaskDataSource();
        dataSource.setGaNames(GAs);
        dataSource.setDbUtil(dbUtil);
    }

    public static void main(String[] args) {
        setUp();
        dbUtil.writeReadyGenerationInfo(Arrays.asList("testGA1", "testGA2"));
        dataSource.start();

    }

    @Test
    public void handles_updating_generation_info_across_two_GAs(){
        setUp();
        dbUtil.writeReadyGenerationInfo(Arrays.asList("testGA1", "testGA2"));
        dataSource.start();
        sleep();

        //Gen 1
        putNewGeneration("testGA1", 1L);
        putNewGeneration("testGA2", 1L);

        sleep();

        MultiGAExperimentTask nextTask = dataSource.getNextTask();
        assertEquals(1L, nextTask.getGenId());

        nextTask = dataSource.getNextTask();
        assertEquals(1L, nextTask.getGenId());


        //Gen 2 - assymetric
        putNewGeneration("testGA1", 2L);
        sleep();
        nextTask = dataSource.getNextTask();
        assertEquals("testGA1", nextTask.getGaName());
        assertEquals(2L, nextTask.getGenId());
    }

    private void sleep() {
        ThreadUtil.sleep(500);
    }

    private void putNewGeneration(String gaName, long genId) {
        dbUtil.writeTaskToDo(taskId,0,0, gaName, genId);
        taskId++;
        dbUtil.updateReadyGenerationInfo(gaName, genId);
    }

    private MultiGAExperimentTask testTask(String testGA1) {
        MultiGAExperimentTask taskForGA1 = new MultiGAExperimentTask();
        taskForGA1.setGaName(testGA1);
        return taskForGA1;
    }
}