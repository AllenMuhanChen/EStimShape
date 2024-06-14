package org.xper.intan;

import org.xper.Dependency;

/**
 * @author Allen Chen
 *
 * Provides experiment-relevant control of recording functions of Intan:
 * - starting and stopping recording
 * - changing save path / filename
 * - live notes
 *
 * This CAN be used with an Intan RHS board, but will only provide the recording functionality.
 */
public class IntanRHD {

    @Dependency
    protected IntanClient intanClient;

    @Dependency
    private String defaultSavePath;

    @Dependency
    private String defaultBaseFileName;

    public void connect() {
        intanClient.connect();
    }

    public void disconnect() {
        intanClient.disconnect();
    }

    public void record(){
        //path has not been set yet in the Intan software
        if(intanClient.isBlank("Filename.Path")){
            setSavePath(defaultSavePath);
        }
        //baseFileName has not been set yet in the Intan software
        if(intanClient.isBlank("Filename.BaseFilename")){
            setBaseFilename(defaultBaseFileName);
        }
        runMode("Record");
    }

    /**
     * Stop saving of data to disk and playback of neural data
     */
    public void stop(){
        runMode("Stop");
    }

    /**
     * Stops saving of data to disk but keeps playback of neural data going
     */
    public void stopRecording(){
        runMode("Run");
    }

    public void setSavePath(String path) {
        runMode("Stop"); //runMode needs to be Stop before Path can be changed
        intanClient.set("Filename.Path", path);
    }

    public void setBaseFilename(String baseFilename){
        runMode("Stop");
        intanClient.set("Filename.BaseFilename", baseFilename);
    }

    public void writeNote(String note){
        intanClient.writeNote(note);
    }
    /**
     * @param mode: "Run", "Stop", "Record", or "Trigger"
     */
    private void runMode(String mode) {
        if(mode.equalsIgnoreCase("Stop")){
            if (!isRunMode("Stop")) {
                setMode(mode);
            }
        } else{
            runMode("Stop"); //Can only set to Run, Record, or Trigger if current mode is Stop
            setMode(mode);
        }
    }

    private void setMode(String mode) {
        if (!isRunMode(mode)) {
            waitForUpload();
            intanClient.set("runmode", mode);
        }
    }

    /**
     * @param mode: "Run", "Stop", "Record", or "Trigger"
     */
    private boolean isRunMode(String mode) {
        String currentMode = intanClient.get("runmode");
        if (currentMode.equalsIgnoreCase(mode)) {
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
    public void waitForUpload() {
        intanClient.waitFor(new Condition() {
            @Override
            public boolean check() {
                return !isUploadInProgress();
            }
        });
    }

    private boolean isUploadInProgress() {
        String uploadInProgress = intanClient.get("uploadinprogress");
        if (uploadInProgress.equalsIgnoreCase("True"))
            return true;
        else
            return false;
    }

    public String getSavePath(){
        return intanClient.get("Filename.Path");
    }

    public String getBaseFilename(){
        return intanClient.get("Filename.Path");
    }

    public void setIntanClient(IntanClient intanClient) {
        this.intanClient = intanClient;
    }

    public String getDefaultSavePath() {
        return defaultSavePath;
    }

    public void setDefaultSavePath(String defaultPath) {
        this.defaultSavePath = defaultPath;
    }

    public String getDefaultBaseFileName() {
        return defaultBaseFileName;
    }

    public void setDefaultBaseFileName(String defaultBaseFileName) {
        this.defaultBaseFileName = defaultBaseFileName;
    }

    public IntanClient getIntanClient() {
        return intanClient;
    }
}