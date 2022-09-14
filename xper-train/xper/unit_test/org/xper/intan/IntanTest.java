package org.xper.intan;

import org.junit.BeforeClass;
import org.junit.Test;
import org.xper.time.TestingTimeUtil;
import org.xper.util.ThreadUtil;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public class IntanTest {

    private static IntanClient intanClient;
    private static IntanController intanController;

    private static final TestingTimeUtil timeUtil = new TestingTimeUtil();
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

        intanController.connect();
    }

    @Test
    public void intan_controller_starts_and_stops_recording(){
        timeUtil.tic();
        intanController.startRecording();
        timeUtil.toc();
        String runmode = intanClient.get("runmode");
        assertTrue(intanController.isRecording());
        System.out.println("Time to Start Recording: " + timeUtil.elapsedTimeMillis() + " ms");

        timeUtil.tic();
        intanController.stopRecording();
        timeUtil.toc();
        runmode = intanClient.get("runmode");
        assertTrue(!intanController.isRecording());
        System.out.println("Time to Stop Recording: " + timeUtil.elapsedTimeMillis() + " ms");
    }

    @Test
    public void intan_client_test_get(){
        String msg = intanClient.get("type");

        assertTrue(msg, msg.contains("Controller"));

    }

    @Test
    public void intan_client_test_set(){
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
