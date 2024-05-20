package org.xper.allen.pga;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.Dependency;
import org.xper.allen.Stim;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;

import org.xper.allen.util.MultiGaDbUtil;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.exception.VariableNotFoundException;
import org.xper.util.FileUtil;
import org.xper.util.ThreadUtil;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class FromDbGABlockGenerator extends AbstractMStickPngTrialGenerator<Stim> {
    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    Integer numTrialsPerStimulus;

    @Dependency
    String gaName;

    @Dependency
    ReceptiveFieldSource rfSource;

    @Dependency
    int numCatchTrials;

    @Dependency
    RFStrategy rfStrategy = RFStrategy.PARTIALLY_INSIDE;

    //Parameters
    private RGBColor color;

    public static void main(String[] args) {
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.ga.config_class"));
        FromDbGABlockGenerator generator = context.getBean(FromDbGABlockGenerator.class);

        int r = Integer.parseInt(args[0]);
        int g = Integer.parseInt(args[1]);
        int b = Integer.parseInt(args[2]);

        generator.setColor(new RGBColor(r/255f,g/255f,b/255f));

        generator.generate();
    }

    @Override
    protected void addTrials() {
        Coordinates2D initialCoords = new Coordinates2D(0, 0);

        // Read database to find stim_ids from StimGaInfo that don't have a StimSpec
        Long experimentId = dbUtil.readCurrentExperimentId(gaName);
        List<Long> lineageIdsInThisExperiment = dbUtil.readLineageIdsForExperiment(experimentId);

        addCatchLineage(lineageIdsInThisExperiment);

        List<Long> stimIdsToGenerate = dbUtil.findStimIdsWithoutStimSpec(lineageIdsInThisExperiment);

        // For each stim_id, read the stim_type and magnitude
        System.out.println("StimIds to Generate: " + stimIdsToGenerate.size());
        for (Long stimId : stimIdsToGenerate) {
            StimGaInfoEntry stimInfo = dbUtil.readStimGaInfoEntry(stimId);
            StimType stimType = StimType.valueOf(stimInfo.getStimType());
            double magnitude = stimInfo.getMutationMagnitude();
            Long parentId = stimInfo.getParentId();

            System.out.println("StimId: " + stimId + " StimType: " + stimType + " Magnitude: " + magnitude);

            // Create a new Stim object with the stim_type and magnitude (if applicable)
            Stim stim;
            if(stimType.equals(StimType.REGIME_ZERO)){
                stim = new SeedingStim(stimId, this, initialCoords, "SHADE", color, rfStrategy);
            }
            else if (stimType.equals(StimType.REGIME_ZERO_2D))
            {
                stim = new SeedingStim(stimId, this, initialCoords, "2D", color, rfStrategy);
            }
            else if(stimType.equals(StimType.REGIME_ONE)){
                stim = new GrowingStim(stimId, this, parentId, initialCoords, magnitude, "SHADE", color, rfStrategy);
            }
            else if(stimType.equals(StimType.REGIME_ONE_2D)){
                stim = new GrowingStim(stimId, this, parentId, initialCoords, magnitude, "2D", color, rfStrategy);
            }
            else if(stimType.equals(StimType.REGIME_TWO)){
                stim = new PruningStim(stimId, this, parentId, initialCoords, "SHADE", color, rfStrategy);
            }
            else if(stimType.equals(StimType.REGIME_TWO_2D)){
                stim = new PruningStim(stimId, this, parentId, initialCoords, "2D", color, rfStrategy);
            }
            else if(stimType.equals(StimType.REGIME_THREE)){
                stim = new LeafingStim(stimId, this, parentId, initialCoords, magnitude, "SHADE", color, rfStrategy);
            }
            else if(stimType.equals(StimType.REGIME_THREE_2D)){
                stim = new LeafingStim(stimId, this, parentId, initialCoords, magnitude, "2D", color, rfStrategy);
            }
            else if (stimType.equals(StimType.CATCH)){
                stim = new CatchStim(stimId, this);
            }
            else{
                throw new RuntimeException("Stim Type not recognized");
            }

            stims.add(stim);
        }

//        if (isFirstGen()) {
//            addCatchTrials();
//        }

        System.err.println("Number of stims to generate: " + stims.size());
    }

    private static void addCatchLineage(List<Long> lineageIdsInThisExperiment) {
        lineageIdsInThisExperiment.add(0L);
    }

    private boolean isFirstGen() {
        return dbUtil.readStimGaInfo(stims.get(0).getStimId()).getGenId() == 1;
    }

    private void addCatchTrials() {
        for (int i = 0; i < numCatchTrials; i++) {
            CatchStim stim = new CatchStim(getGlobalTimeUtil().currentTimeMicros(), this);
            stims.add(stim);
            ThreadUtil.sleep(1);
        }
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
        List<Long> allStimIds = new ArrayList<>();

        //Write All Stims into StimSpec and build list of stimIds (which includes reps)
        for (Stim stim : getStims()) {
            Long stimId = stim.getStimId();
            stim.writeStim();
            for (int i = 0; i < numTrialsPerStimulus; i++) {
                allStimIds.add(stimId);
            }
        }

        //shuffle allStimIds
        Collections.shuffle(allStimIds);

        //Write allStimIds into TaskToDo
        long lastTaskId = -1L;
        for (Long stimId : allStimIds) {
            long taskId = getGlobalTimeUtil().currentTimeMicros();
            while (taskId == lastTaskId) {
                taskId = getGlobalTimeUtil().currentTimeMicros();
            }

            dbUtil.writeTaskToDo(taskId, stimId, -1, getGaName(), genId);
        }
    }

    @Override
    public MultiGaDbUtil getDbUtil() {
        return dbUtil;
    }

    public ReceptiveField getReceptiveField(){
        return rfSource.getReceptiveField();
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

    public String getGaName() {
        return gaName;
    }

    public void setGaName(String gaName) {
        this.gaName = gaName;
    }

    public ReceptiveFieldSource getRfSource() {
        return rfSource;
    }

    public void setRfSource(ReceptiveFieldSource rfSource) {
        this.rfSource = rfSource;
    }

    public void setColor(RGBColor color) {
        this.color = color;
    }

    public int getNumCatchTrials() {
        return numCatchTrials;
    }

    public void setNumCatchTrials(int numCatchTrials) {
        this.numCatchTrials = numCatchTrials;
    }
}