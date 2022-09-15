package org.xper.intan;

import org.junit.BeforeClass;
import org.junit.Test;
import org.xper.Dependency;
import org.xper.time.TestingTimeUtil;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

/**
 * @author Allen Chen
 */
public class IntanTest {

    private static IntanClient intanClient;
    private static IntanController intanController;

    private static final TestingTimeUtil timeUtil = new TestingTimeUtil();

    @Dependency
    static String intanPath = "/home/i2_allen/Documents/Test";
    /**
     * Before all of these tests will pass:
     * 1. The Intan Box needs to be turned ON
     * 2. The Intan Software needs to be open
     * 3. The Intan TCP server needs to be listening for new connections.
     *    Do this by pressing the "Connect" button, found under "Network"
     *    in the tool bar.
     */
    @BeforeClass
    public static void set_up(){
        intanClient = new IntanClient();
        intanController = new IntanController();
        intanController.setIntanClient(intanClient);
        intanController.setDefaultPath(intanPath);

        intanController.connect();
    }

    @Test
    public void test_intan_controller_change_path(){
        String path = "fooPath";
        intanController.setPath(path);
        assertEquals(path, intanClient.get("Filename.Path"));
    }

    @Test
    public void test_intan_controller_change_filebasename(){
        String basename = "barBase";
        intanController.setBaseFilename(basename);
        assertEquals(basename, intanClient.get("Filename.BaseFilename"));
    }

    @Test
    public void test_empty(){
        System.out.println(intanClient.get("Filename.BaseFilename"));
    }

    @Test
    public void test_record_defaults(){
        intanController.record();
    }

//    @Ignore("intanController's setRunMode methods already ensure" +
//            "that the runmode isTrue set before terminating. Run this manually " +
//            "to test timing.")
//    @Test
//    public void test_intan_controller_runModeRun_timing(){
//        timeUtil.tic();
//        intanController.runMode("Run");
//        timeUtil.toc();
//        assertTrue(intanController.isRunMode("Run"));
//        System.out.println("Time to Start Recording: " + timeUtil.elapsedTimeMillis() + " ms");
//
//        timeUtil.tic();
//        intanController.runMode("Stop");
//        timeUtil.toc();
//        assertTrue(intanController.isRunMode("Stop"));
//        System.out.println("Time to Stop Recording: " + timeUtil.elapsedTimeMillis() + " ms");
//    }


    @Test
    public void intan_client_test_get_set(){
        intanClient.set("fileformat", "onefilepersignaltype");

        String fileformat = intanClient.get("fileformat");

        assertTrue(fileformat, fileformat.contains("OneFilePerSignalType"));
    }

    @Test
    public void intan_client_handles_opening_conection_while_connection_already_open(){
        intanClient.connect();
        intanClient.connect();
        intanClient.connect();
    }


}
