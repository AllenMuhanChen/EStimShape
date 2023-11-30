package org.xper.allen.pga;

import org.xper.Dependency;
import org.xper.allen.Stim;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;

import org.xper.allen.util.MultiGaDbUtil;
import org.xper.drawing.Coordinates2D;
import org.xper.exception.VariableNotFoundException;

import java.util.List;

public class FromDbGABlockGenerator extends AbstractMStickPngTrialGenerator<Stim> {
    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    Integer numTrialsPerStimulus;

    @Dependency
    private double initialSize;

    @Dependency
    private Coordinates2D intialCoords;

    @Dependency
    String gaName;



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
            Long parentId = stimInfo.getParentId();

            System.out.println("StimId: " + stimId + " StimType: " + regimeType + " Magnitude: " + magnitude);

            // Create a new Stim object with the stim_type and magnitude (if applicable)
            Stim stim;
            if(regimeType.equals(RegimeType.REGIME_ZERO)){
                stim = new RegimeZeroStim(stimId, this, initialSize, intialCoords);
            }
            else if(regimeType.equals(RegimeType.REGIME_ONE)){
                stim = new RegimeOneStim(stimId, this, parentId, initialSize, intialCoords, magnitude);
            }
            else if(regimeType.equals(RegimeType.REGIME_TWO)){
                stim = new RegimeTwoStim(stimId, this, parentId, initialSize, intialCoords);
            }
            else if(regimeType.equals(RegimeType.REGIME_THREE)){
                stim = new RegimeThreeStim(stimId, this, parentId, initialSize, intialCoords, magnitude);
            }
            else{
                throw new RuntimeException("Regime Type not recognized");
            }

            stims.add(stim);
        }

        System.err.println("Number of stims to generate: " + stims.size());
    }

    @Override
    protected void updateReadyGeneration() {
        getDbUtil().updateReadyGAsAndGenerationsInfo(gaName, genId);

        System.out.println("Done Generating...");
    }

    @Override
    protected void updateGenId() {
        try {
			/*
			  Gen ID is important for xper to be able to load new tasks on the fly. It will only do so if the generation Id is upticked.
			 */
            genId = getDbUtil().readMultiGAReadyGenerationInfo().getGenIdForGA(gaName) + 1;
        } catch (VariableNotFoundException e) {
            getDbUtil().writeReadyGenerationInfo(0, 0);
        }
    }

    @Override
    protected void writeTrials(){
        for (Stim stim : getStims()) {
            stim.writeStim();
            Long stimId = stim.getTaskId();
            for (int i = 0; i < numTrialsPerStimulus; i++) {
                long taskId = getGlobalTimeUtil().currentTimeMicros();
                dbUtil.writeTaskToDo(taskId, stimId, -1, gaName, genId);
            }
        }
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

    public double getInitialSize() {
        return initialSize;
    }

    public void setInitialSize(double initialSize) {
        this.initialSize = initialSize;
    }

    public Coordinates2D getIntialCoords() {
        return intialCoords;
    }

    public void setIntialCoords(Coordinates2D intialCoords) {
        this.intialCoords = intialCoords;
    }

    public String getGaName() {
        return gaName;
    }

    public void setGaName(String gaName) {
        this.gaName = gaName;
    }
}