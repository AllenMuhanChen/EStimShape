package org.xper.intan;

import org.xper.Dependency;
import org.xper.util.ThreadUtil;

/**
 * Provides experiment-relevant control of Intan
 */
public class IntanController {

    public static final int QUERY_INTERVAL = 100;
    @Dependency
    private IntanClient intanClient;

    public void connect(){
        intanClient.connect();
    }

    public void disconnect(){
        intanClient.disconnect();
    }

    public void startRecording(){
        if(!isRecording()) {
            intanClient.set("runmode", "run");
        } else{
            System.err.println("Intan already recording, did not set runmode");
        }
        ThreadUtil.sleep(QUERY_INTERVAL);
        while(!isRecording()){
            ThreadUtil.sleep(QUERY_INTERVAL);
        }
    }

    public void stopRecording(){
        if(isRecording()) {
            intanClient.set("runmode", "stop");
        } else{
            System.err.println("Intan already stopped recording, did not set runmode");
        }

        ThreadUtil.sleep(QUERY_INTERVAL);
        while(isRecording()){
            ThreadUtil.sleep(QUERY_INTERVAL);
        }
    }

    public boolean isRecording(){
        String runmode = intanClient.get("runmode");
        if(runmode.contains("RunMode Run")){
            return true;
        } else{
            return false;
        }
    }

    public IntanClient getIntanClient() {
        return intanClient;
    }

    public void setIntanClient(IntanClient intanClient) {
        this.intanClient = intanClient;
    }

}
