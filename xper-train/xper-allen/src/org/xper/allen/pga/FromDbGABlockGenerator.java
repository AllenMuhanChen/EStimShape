package org.xper.allen.pga;

import org.xper.Dependency;
import org.xper.allen.Stim;
import org.xper.allen.ga3d.blockgen.GABlockGenerator;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.util.MultiGaDbUtil;

import java.util.List;

public class FromDbGABlockGenerator<T extends Stim> extends AbstractMStickPngTrialGenerator<T> {

    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    Integer numTrialsPerStimulus;

    String gaName = "New3D";

    @Override
    protected void addTrials() {
        // Read database to find stim_ids from StimGaInfo that don't have a StimSpec
        Long experimentId = dbUtil.readCurrentExperimentId(gaName);
        List<Long> lineageIdsInThisExperiment = dbUtil.readLineageIdsForExperiment(experimentId);
        List<Long> stimIdsToGenerate = dbUtil.findStimIdsWithoutStimSpec(lineageIdsInThisExperiment);

        // For each stim_id, read the stim_type and magnitude
        for (Long stimId : stimIdsToGenerate) {
            StimGaInfoEntry stimInfo = dbUtil.readStimGaInfoEntry(stimId);
            RegimeType regimeType = RegimeType.valueOf(stimInfo.getStimType());
            double magnitude = stimInfo.getMutationMagnitude();

            System.out.println("StimId: " + stimId + " StimType: " + regimeType + " Magnitude: " + magnitude);
        }

            // Create a new Stim object with the stim_type and magnitude (if applicable)




    }

    @Override
    public MultiGaDbUtil getDbUtil() {
        return dbUtil;
    }

    public void setDbUtil(MultiGaDbUtil dbUtil) {
        this.dbUtil = dbUtil;
    }

    public Integer getNumTrialsPerStimulus() {
        return numTrialsPerStimulus;
    }

    public void setNumTrialsPerStimulus(Integer numTrialsPerStimulus) {
        this.numTrialsPerStimulus = numTrialsPerStimulus;
    }
}