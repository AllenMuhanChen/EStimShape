package org.xper.allen.ga3d.blockgen;

import org.xper.Dependency;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.util.MultiGaDbUtil;

import java.util.ArrayList;
import java.util.List;

/**
 * Abstract class for GA Block generation that relies on MultiDbGaUtil
 */
public abstract class GABlockGenerator<T extends ThreeDGAStim> extends AbstractMStickPngTrialGenerator<T> {
    public static String GA_NAME;
    protected Integer numTrialsPerStimulus;

    @Dependency
    protected MultiGaDbUtil dbUtil;

    List<T> stims = new ArrayList<>();

    @Override
    public MultiGaDbUtil getDbUtil() {
        return dbUtil;
    }


    @Override
    protected void updateReadyGeneration() {
        getDbUtil().updateReadyGAsAndGenerationsInfo(getGaBaseName(), genId);

        System.out.println("Done Generating...");
    }

    @Override
    protected void updateGenId(){
        Long genId;
        try {
            genId = getDbUtil().readMultiGAReadyGenerationInfo().getGenIdForGA(getGaBaseName()) + 1;
        } catch (Exception e) {
            getDbUtil().writeReadyGAandGenerationInfo(getGaBaseName());
            genId = 0L;
        }
        this.genId = genId;
    }

    @Override
    protected void writeTrials(){
        for (T stim : getStims()) {
            stim.writeStim();
            stim.writeGaInfo(getGaBaseName(), genId);
            Long stimId = stim.getStimId();
            for (int i = 0; i < numTrialsPerStimulus; i++) {
                long taskId = getGlobalTimeUtil().currentTimeMicros();
                dbUtil.writeTaskToDo(taskId, stimId, -1, getGaBaseName(), genId);
            }
        }
    }

    public void setDbUtil(MultiGaDbUtil dbUtil) {
        this.dbUtil = dbUtil;
    }

    public String getGaBaseName() {
        return GA_NAME;
    }

    @Override
    public List<T> getStims() {
        return stims;
    }

    @Override
    public void setStims(List<T> stims) {
        this.stims = stims;
    }

    public Integer getNumTrialsPerStimulus() {
        return numTrialsPerStimulus;
    }

    public void setNumTrialsPerStimulus(Integer numTrialsPerStimulus) {
        this.numTrialsPerStimulus = numTrialsPerStimulus;
    }
}