package org.xper.intan;

import org.junit.BeforeClass;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.time.TestingTimeUtil;
import org.xper.util.FileUtil;
import org.xper.util.ThreadUtil;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

/**
 * @author Allen Chen
 */
public class IntanTest {

    private static IntanClient intanClient;
    private static IntanRHD intanRHD;

    private static final TestingTimeUtil timeUtil = new TestingTimeUtil();

    /**
     * Before all of these tests will pass:
     * 1. The Intan Box needs to be turned ON
     * 2. The Intan Software needs to be open
     * 3. There NEEDS to be a headstage plugged in or the Intan Software will occaisonally crash
     *    with segmentation fault errors when setting runmode
     * 4. The Intan TCP server needs to be listening for new connections.
     *    Do this by pressing the "Connect" button, found under "Network"
     *    in the tool bar.
     * 4.5. Change the "Host" ip from 127.0.0.1 to the local ip4 address of the computer
     */
    @BeforeClass
    public static void set_up(){
        FileUtil.loadTestSystemProperties("/xper.properties.test");
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(FileUtil.loadConfigClass("test.experiment.config_class"));
        intanClient = context.getBean(IntanClient.class);
        intanRHD = context.getBean(IntanRHD.class, "intan");
        intanRHD.connect();
    }

    @Test
    public void record_uses_default_path_and_basefilename(){
        intanClient.clear("Filename.BaseFilename");
        intanClient.clear("Filename.Path");

        timeUtil.tic();
        intanRHD.record();
        timeUtil.toc();
        System.out.println("Time to Start Recording: " + timeUtil.elapsedTimeMillis() + " ms");

        ThreadUtil.sleep(1000);

        timeUtil.tic();
        intanRHD.stop();
        timeUtil.toc();
        System.out.println("Time to Stop Recording: " + timeUtil.elapsedTimeMillis() + " ms");

        //TODO: assert that the file(s) were created?
        assertEquals(intanRHD.getDefaultSavePath(), intanClient.get("Filename.Path"));
        assertEquals(intanRHD.getDefaultBaseFileName(), intanClient.get("Filename.BaseFilename"));
    }

    @Test
    public void get_on_empty_parameter_returns_empty_string(){
        intanClient.clear("Filename.BaseFilename");
        assertTrue(intanClient.get("Filename.BaseFilename").isEmpty());
    }


    @Test
    public void intan_client_handles_opening_conection_while_connection_already_open(){
        timeUtil.tic();
        intanClient.connect();
        timeUtil.toc();
        System.out.println("Took " + timeUtil.elapsedTimeMillis() + "ms to check and maintain connection");

        timeUtil.tic();
        intanClient.connect();
        timeUtil.toc();
        System.out.println("Took " + timeUtil.elapsedTimeMillis() + "ms to check and maintain connection");

        timeUtil.tic();
        intanClient.connect();
        timeUtil.toc();
        System.out.println("Took " + timeUtil.elapsedTimeMillis() + "ms to check and maintain connection");
    }

    @Test
    public void intan_switches_from_recording_to_playback(){
        intanRHD.record();
        intanRHD.stopRecording();

        assertTrue(intanClient.get("RunMode").equalsIgnoreCase("Run"));

        intanRHD.stop();
    }
}