package org.xper.allen.pga;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.Dependency;
import org.xper.allen.Stim;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;

import org.xper.allen.pga.sidetest.SideTestStim;
import org.xper.allen.twodvsthreed.TwoDVsThreeDStim;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.exception.VariableNotFoundException;
import org.xper.util.FileUtil;
import org.xper.util.ThreadUtil;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

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
        int r;
        int g;
        int b;
        try {
            r = Integer.parseInt(args[0]);
            g = Integer.parseInt(args[1]);
            b = Integer.parseInt(args[2]);
        } catch (Exception e) {
            System.err.println("Error parsing RGB values. Using default color.");
            r = 255;
            g = 255;
            b = 255;
        }

        generator.setColor(new RGBColor(r/255f,g/255f,b/255f));

        generator.generate();
    }

    @Override
    protected void addTrials() {
        Coordinates2D pngCoordinates = new Coordinates2D(0, 0); //we want this (0,0) by convention and change location of drawn objects within the image itself


        // Read database to find stim_ids from StimGaInfo that don't have a StimSpec
        Long experimentId = dbUtil.readCurrentExperimentId(gaName);
        List<Long> lineageIdsInThisExperiment = dbUtil.readLineageIdsForExperiment(experimentId);

        addCatchLineage(lineageIdsInThisExperiment);

        List<Long> stimIdsToGenerate = dbUtil.findStimIdsWithoutStimSpec(lineageIdsInThisExperiment);

        // For each stim_id, read the stim_type and magnitude
        System.out.println("StimIds to Generate: " + stimIdsToGenerate.size());
        for (Long stimId : stimIdsToGenerate) {
            StimGaInfoEntry stimInfo = dbUtil.readStimGaInfoEntry(stimId);
            double magnitude = stimInfo.getMutationMagnitude();
            Long parentId = stimInfo.getParentId();

            //For the cases where the type is an ENUM type
            parseZooming(stimId, stimInfo, parentId);
            parseCatch(stimId, stimInfo);
            parseGaStim(stimId, stimInfo, parentId, magnitude);
            parseSideTest(stimId, stimInfo, parentId);


        }

        System.err.println("Number of stims to generate: " + stims.size());
    }

    private void parseCatch(Long stimId, StimGaInfoEntry stimInfo) {
        StimType stimType = StimType.valueOf(stimInfo.getStimType());
        if (stimType.equals(StimType.CATCH)){
            Stim stim = new CatchStim(stimId, this);
            stims.add(stim);
        }
    }

    private void parseSideTest(Long stimId, StimGaInfoEntry stimInfo, Long parentId) {
        Stim stim = null;
        StimType stimType;

        try {
            stimType = StimType.valueOf(stimInfo.getStimType());
        } catch (IllegalArgumentException e) {
            return;
        }
        if (stimType.equals(StimType.SIDETEST_2Dvs3D_2D_HIGH) ||
                stimType.equals(StimType.SIDETEST_2Dvs3D_2D_LOW) ||
                stimType.equals(StimType.SIDETEST_2Dvs3D_3D_SHADE) ||
                stimType.equals(StimType.SIDETEST_2Dvs3D_3D_SPECULAR)
        ) {
            stim = new SideTestStim(stimId, this, parentId, stimType);
            stims.add(stim);
        }
    }

    private void parseGaStim(Long stimId, StimGaInfoEntry stimInfo, Long parentId, double magnitude) {
        Stim stim = null;
        StimType stimType = StimType.valueOf(stimInfo.getStimType());
        if(stimType.equals(StimType.REGIME_ZERO)){
            stim = new SeedingStim(stimId, this, "3D", color);
        }
        else if (stimType.equals(StimType.REGIME_ZERO_2D))
        {
            stim = new SeedingStim(stimId, this, "2D", color);
        }
        else if(stimType.equals(StimType.REGIME_ONE)){
            stim = new GrowingStim(stimId, this, parentId, magnitude, "3D");
        }
        else if(stimType.equals(StimType.REGIME_ONE_2D)){
            stim = new GrowingStim(stimId, this, parentId, magnitude, "2D");
        }
        else if(stimType.equals(StimType.REGIME_TWO)){
            stim = new PruningStim(stimId, this, parentId, "3D");
        }
        else if(stimType.equals(StimType.REGIME_TWO_2D)){
            stim = new PruningStim(stimId, this, parentId, "2D");
        }
        else if(stimType.equals(StimType.REGIME_THREE)){
            stim = new LeafingStim(stimId, this, parentId, magnitude, "3D");
        }
        else if(stimType.equals(StimType.REGIME_THREE_2D)){
            stim = new LeafingStim(stimId, this, parentId, magnitude, "2D");
        }
        if (stim != null) {
            stims.add(stim);
        }
    }

    private void parseZooming(Long stimId, StimGaInfoEntry stimInfo, Long parentId) {
        String stimTypeString = stimInfo.getStimType();

        // Check for "Zooming_x" pattern
        Pattern pattern = Pattern.compile("Zooming_(\\d+)");
        Matcher matcher = pattern.matcher(stimTypeString);
        if (matcher.matches()) {
            int zoomingValue = Integer.parseInt(matcher.group(1));
            System.out.println("Detected Zooming_x with x = " + zoomingValue);

            stims.add(new ZoomingStim(stimId, this, parentId, zoomingValue, "3D"));
        }
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
            lastTaskId = taskId;

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