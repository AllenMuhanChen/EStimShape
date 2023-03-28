package org.xper.allen.ga3d.blockgen;

import org.xper.Dependency;
import org.xper.allen.Stim;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.util.MultiGaDbUtil;

import java.util.ArrayList;
import java.util.List;

public abstract class GABlockGenerator extends AbstractMStickPngTrialGenerator<ThreeDGAStim> {
    public static String GA_NAME;
    protected Integer numTrialsPerStimuli;

    @Dependency
    MultiGaDbUtil dbUtil;

    List<ThreeDGAStim> stims = new ArrayList<>();

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
        for (ThreeDGAStim stim : getStims()) {
            stim.writeStim();
            stim.writeGaInfo(getGaBaseName(), genId);
            Long stimId = stim.getStimId();
            for (int i = 0; i < numTrialsPerStimuli; i++) {
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

    public List<ThreeDGAStim> getStims() {
        return stims;
    }

    public void setStims(List<ThreeDGAStim> stims) {
        this.stims = (List<ThreeDGAStim>) stims;
    }
}