package org.xper.intan;

import org.xper.Dependency;
import org.xper.util.ThreadUtil;

/**
 * @author Allen Chen
 *
 * Provides experiment-relevant control of Intan
 */
public class IntanController {

    private static final int QUERY_INTERVAL = 10;

    @Dependency
    private IntanClient intanClient;

    public void connect(){
        intanClient.connect();
    }

    public void disconnect(){
        intanClient.disconnect();
    }

    /**
     * Controller acquires data, which is only displayed graphically and not saved to disk
     */
    public void runModeRun(){
        if(!isRunModeRun()) {
            intanClient.set("runmode", "run");
        } else{
            System.err.println("Intan already running, did not set runmode to runModeRun");
        }
        ThreadUtil.sleep(QUERY_INTERVAL);
        while(!isRunModeRun()){
            ThreadUtil.sleep(QUERY_INTERVAL);
        }
    }

    /**
     * Controller acquires data, which is displayed graphically and saved to disk
     */
    public void runModeRecord(){
        if(!isRunModeRecord()) {
            intanClient.set("runmode", "record");
        } else{
            System.err.println("Intan already recording, did not set runmode to runModeRecord");
        }
        ThreadUtil.sleep(QUERY_INTERVAL);
        while(!isRunModeRecord()){
            ThreadUtil.sleep(QUERY_INTERVAL);
        }
    }

    /**
     * Controller acquires data, which is displayed graphically, and waits for a trigger event
     * to begin saving to disk
     */
    public void runModeRTrigger(){
        if(!isRunModeTrigger()) {
            intanClient.set("runmode", "trigger");
        } else{
            System.err.println("Intan already recording, did not set runmode to runModeRecord");
        }
        ThreadUtil.sleep(QUERY_INTERVAL);
        while(!isRunModeRecord()){
            ThreadUtil.sleep(QUERY_INTERVAL);
        }
    }

    /**
     * Controller does not acquire data
     */
    public void runModeStop(){
        if(!isRunModeStop()) {
            intanClient.set("runmode", "stop");
        } else{
            System.err.println("Intan already stopped recording, did not set runmode to runModeStop");
        }

        ThreadUtil.sleep(QUERY_INTERVAL);
        while(!isRunModeStop()){
            ThreadUtil.sleep(QUERY_INTERVAL);
        }
    }

    public boolean isRunModeRun(){
        String runmode = intanClient.get("runmode");
        if(runmode.contains("RunMode Run")){
            return true;
        } else{
            return false;
        }
    }

    public boolean isRunModeRecord(){
        String runmode = intanClient.get("runmode");
        if(runmode.contains("RunMode Record")){
            return true;
        } else{
            return false;
        }
    }

    public boolean isRunModeTrigger(){
        String runmode = intanClient.get("runmode");
        if(runmode.contains("RunMode Trigger")){
            return true;
        } else{
            return false;
        }
    }

    public boolean isRunModeStop(){
        String runmode = intanClient.get("runmode");
        if(runmode.contains("RunMode Stop")){
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
