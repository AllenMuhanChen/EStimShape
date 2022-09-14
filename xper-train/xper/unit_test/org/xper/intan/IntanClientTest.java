package org.xper.intan;

import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import org.xper.util.ThreadUtil;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public class IntanClientTest {

    private static IntanClient intanClient;

    /**
     * Before any of these tests will pass, The Intan Software needs to be open
     * and the Intan TCP server needs to be listening for new
     * connections. Do this by pressing the "Connect" button, found under "Network"
     * in the tool bar.
     */
    @BeforeClass
    public static void set_up(){
        intanClient = new IntanClient();
        intanClient.connect();
    }


    @Test
    public void intan_client_test_get(){
        String msg = intanClient.sendMessage("get type");
        System.out.println(msg);


        assertTrue(msg, msg.contains("Controller"));

    }

    
}
