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

    public void connect() {
        intanClient.connect();
    }

    public void disconnect() {
        intanClient.disconnect();
    }

    public void setPath(String path) {
        runMode("Stop"); //runMode needs to be Stop before Path can be changed
        intanClient.set("Filename.Path", path);
    }

    public String getPath() {
        return intanClient.get("Filename.Path");
    }

    public void runMode(String mode) {
        if (!isRunMode(mode)) {
            waitForUpload();
            intanClient.set("runmode", mode);
        } else {
            System.err.println("Intan RunMode is already " + mode + ", did not set runmode");
        }
    }


    /**
     * @param mode: "Run", "Stop", "Record", or "Trigger"
     * @return whether the current runmode is equal to Mode
     */
    public boolean isRunMode(String mode) {
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
            System.out.println("Waiting for Upload");
            ThreadUtil.sleep(IntanClient.QUERY_INTERVAL);
        }
    }

    private boolean isUploadInProgress() {
        String uploadInProgress = intanClient.get("uploadinprogress");
        System.err.println("Upload In Progress: Waiting");
        if (uploadInProgress.equalsIgnoreCase("True"))
            return true;
        else
            return false;
    }

    public IntanClient getIntanClient() {
        return intanClient;
    }

    public void setIntanClient(IntanClient intanClient) {
        this.intanClient = intanClient;
    }

}
