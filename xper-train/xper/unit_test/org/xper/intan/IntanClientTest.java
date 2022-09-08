package org.xper.intan;

import org.junit.Before;
import org.junit.Test;
import org.xper.util.ThreadUtil;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public class IntanClientTest {

    private IntanClient intanClient;

    @Before
    public void set_up(){
        intanClient = new IntanClient();
        intanClient.connect();
    }

    @Test
    public void intan_client_test(){
        String msg = intanClient.sendMessage("Hello World");
        System.out.println(msg);
//        intanClient.stopConnection();
    }

    @Test
    public void intan_client_test_get(){
        String msg = intanClient.sendMessage("get type");
        System.out.println(msg);


        assertTrue(msg, msg.contains("Controller"));

        ThreadUtil.sleep(100000);
    }
}
