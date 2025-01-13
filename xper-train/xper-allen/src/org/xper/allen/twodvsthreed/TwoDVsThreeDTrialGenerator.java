package org.xper.allen.twodvsthreed;

import org.xper.Dependency;
import org.xper.allen.Stim;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.pga.ReceptiveFieldSource;
import org.xper.drawing.RGBColor;
import sun.reflect.generics.reflectiveObjects.NotImplementedException;

import javax.sql.DataSource;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

public class TwoDVsThreeDTrialGenerator extends AbstractMStickPngTrialGenerator<Stim> {
    @Dependency
    DataSource gaDataSource;

    @Dependency
    String gaSpecPath;

    @Dependency
    ReceptiveFieldSource rfSource;


    public int numTrialsPerStim = 5;

    @Override
    protected void addTrials() {
        // TODO: Get top stimuli from GA
        List<Long> stimIdsToTest = fetchStimIdsToTest();
        List<RGBColor> colorsToTest = fetchColorsToTest();
        List<String> textureTypesToTest = Arrays.asList("SHADE", "SPECULAR", "TWOD");

        // GENERATE TRIALS
        for (Long stimId : stimIdsToTest) {
            for (RGBColor color : colorsToTest) {
                for (String textureType : textureTypesToTest) {
                    for (int i = 0; i < numTrialsPerStim; i++) {
                        TwoDVsThreeDStim stim = new TwoDVsThreeDStim(this, stimId, textureType, color);
                        stims.add(stim);
                    }
                }
            }
        }

    }

    @Override
    protected void writeTrials() {
        List<Long> allStimIds = new ArrayList<>();

        for (Stim stim : getStims()) {
            Long stimId = stim.getStimId();
            stim.writeStim();
            for (int i = 0; i < numTrialsPerStim; i++) {
                allStimIds.add(stimId);
            }
        }

        Collections.shuffle(allStimIds);

        long lastTaskId = -1L;
        for (Long stimId : allStimIds) {
            long taskId = getGlobalTimeUtil().currentTimeMicros();
            while (taskId == lastTaskId) {
                taskId = getGlobalTimeUtil().currentTimeMicros();
            }
            lastTaskId = taskId;

            getDbUtil().writeTaskToDo(taskId, stimId, -1, genId);
        }
    }

    private List<RGBColor> fetchColorsToTest() {
        throw new NotImplementedException();
    }

    private List<Long> fetchStimIdsToTest() {
        throw new NotImplementedException();
    }

    public DataSource getGaDataSource() {
        return gaDataSource;
    }

    public void setGaDataSource(DataSource gaDataSource) {
        this.gaDataSource = gaDataSource;
    }

    public String getGaSpecPath() {
        return gaSpecPath;
    }

    public void setGaSpecPath(String gaSpecPath) {
        this.gaSpecPath = gaSpecPath;
    }

    public ReceptiveFieldSource getRfSource() {
        return rfSource;
    }

    public void setRfSource(ReceptiveFieldSource rfSource) {
        this.rfSource = rfSource;
    }
}