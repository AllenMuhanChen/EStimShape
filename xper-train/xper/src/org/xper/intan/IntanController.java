package org.xper.intan;

import org.xper.Dependency;
import org.xper.util.ThreadUtil;

/**
 * @author Allen Chen
 *
 * Provides experiment-relevant control of Intan
 */
public class IntanController {

    @Dependency
    private IntanClient intanClient;



    @Dependency
    private String defaultPath;
    @Dependency
    private String defaultBaseFileName = "Recording";

    public void connect() {
        intanClient.connect();
    }

    public void disconnect() {
        intanClient.disconnect();
    }

    public void record(){
        //path has not been set yet in the Intan software
        if(isEmpty("Filename.Path")){
            setPath(defaultPath);
        }
        //baseFileName has not been set yet in the Intan software
        if(isEmpty("Filename.BaseFilename")){
            setBaseFilename(defaultBaseFileName);
        }
        runMode("Record");
    }

    /**
     * @param parameter
     * @return  true if the specified parameter is not set in the Intan Software
     */
    private boolean isEmpty(String parameter) {
        return intanClient.get(parameter).equalsIgnoreCase(parameter);
    }

    public void stop(){
        runMode("Stop");
    }

    public void setPath(String defaultPath) {
        runMode("Stop"); //runMode needs to be Stop before Path can be changed
        intanClient.set("Filename.Path", defaultPath);
    }

    public void setBaseFilename(String baseFilename){
        runMode("Stop");
        intanClient.set("Filename.BaseFilename", baseFilename);
    }

    /**
     * @param mode: "Run", "Stop", "Record", or "Trigger"
     */
    private void runMode(String mode) {
        if (!isRunMode(mode)) {
            waitForUpload();
            intanClient.set("runmode", mode);
        } else {
            System.err.println("Intan RunMode is already " + mode + ", did not set runmode");
        }
    }

    /**
     * @param mode: "Run", "Stop", "Record", or "Trigger"
     */
    private boolean isRunMode(String mode) {
        String runmode = intanClient.get("runmode");
        if (runmode.equalsIgnoreCase(mode)) {
            return true;
        } else {
            return false;
        }
    }

    /**
     * Setting Run Mode will fail when an upload isTrue in progress, so it's
     * necessary to wait for any uploads to finish first before running any set run mode
     * commands
     */
    private void waitForUpload() {
        while (isUploadInProgress()) {
            System.err.println("Upload In Progress: Waiting");
            ThreadUtil.sleep(IntanClient.QUERY_INTERVAL);
        }
    }

    private boolean isUploadInProgress() {
        String uploadInProgress = intanClient.get("uploadinprogress");
        if (uploadInProgress.equalsIgnoreCase("True"))
            return true;
        else
            return false;
    }


    public void setIntanClient(IntanClient intanClient) {
        this.intanClient = intanClient;
    }

    public String getDefaultPath() {
        return defaultPath;
    }

    public void setDefaultPath(String defaultPath) {
        this.defaultPath = defaultPath;
    }
}
