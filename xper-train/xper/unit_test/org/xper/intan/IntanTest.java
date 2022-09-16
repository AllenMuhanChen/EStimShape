package org.xper.intan;

import org.junit.BeforeClass;
import org.junit.Test;
import org.xper.Dependency;
import org.xper.time.TestingTimeUtil;
import org.xper.util.ThreadUtil;

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
    static String savePath = "/home/i2_allen/Documents/Test";
    @Dependency
    static String baseFilename = "TestRecording";
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
        intanController.setDefaultPath(savePath);
        intanController.setDefaultBaseFileName(baseFilename);

        intanController.connect();
    }

    @Test
    public void test_intan_controller_change_filename(){
        String path = "fooPath";
        intanController.setPath(path);
        assertEquals(path, intanClient.get("Filename.Path"));

        String basename = "barBase";
        intanController.setBaseFilename(basename);
        assertEquals(basename, intanClient.get("Filename.BaseFilename"));
    }

    @Test
    public void get_on_empty_parameter_returns_empty_string(){
        intanClient.clear("Filename.BaseFilename");
        assertTrue(intanClient.get("Filename.BaseFilename").isEmpty());

    }

    @Test
    public void record_uses_default_path_and_basefilename(){
        intanClient.clear("Filename.BaseFilename");
        intanClient.clear("Filename.Path");

        timeUtil.tic();
        intanController.record();
        timeUtil.toc();
        System.out.println("Time to Start Recording: " + timeUtil.elapsedTimeMillis() + " ms");

        ThreadUtil.sleep(1000);

        timeUtil.tic();
        intanController.stop();
        timeUtil.toc();
        System.out.println("Time to Stop Recording: " + timeUtil.elapsedTimeMillis() + " ms");

        //TODO: assert that the file(s) were created?
        assertEquals(savePath, intanClient.get("Filename.Path"));
        assertEquals(baseFilename, intanClient.get("Filename.BaseFilename"));
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
    public void intan_client_gets_and_sets(){
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
