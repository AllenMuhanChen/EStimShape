package org.xper.allen.ga3d.blockgen;

import org.xper.Dependency;
import org.xper.allen.ga.MultiGaGenerationInfo;
import org.xper.allen.ga.ParentSelector;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.Trial;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.drawing.Coordinates2D;
import org.xper.exception.VariableNotFoundException;

import java.util.LinkedList;
import java.util.List;
import java.util.Map;

public class GA3DBlockGen extends AbstractMStickPngTrialGenerator {

    @Dependency
    MultiGaDbUtil dbUtil;
    @Dependency
    ParentSelector parentSelector;

    private String gaName;
    private List<Trial> trials = new LinkedList<>();
    private double initialSize;
    private Coordinates2D initialCoords;
    private int numTrials;
    protected List<String> channels;

    List<Long> stimsToMorph;

    /**
     *
     * @param linNumber - which lineage is being generated.
     * @param numTrials - number of trials per generations
     * @param initialSize - initial size of stimuli in GA
     * @param initialCoords - initial coordinates of stimuli in GA
     * @param channels - list of channels to analyze for parent selection
     */
    public void setUp(int linNumber, int numTrials, double initialSize, Coordinates2D initialCoords, List<String> channels){
        this.numTrials = numTrials;
        this.initialSize = initialSize;
        this.initialCoords = initialCoords;
        this.gaName = "3D-"+Integer.toString(linNumber);
        this.channels = channels;
    }

    @Override
    protected void addTrials() {
        System.out.println(firstGeneration());
        if(firstGeneration()){
            addFirstGeneration();
        } else{
            addNthGeneration();
        }
    }

    private void addFirstGeneration(){
        trials.addAll(createRandTrials(this, numTrials, initialSize, initialCoords));
    }

    private List<Trial> createRandTrials(GA3DBlockGen generator, int numTrials, double size, Coordinates2D coords){
        List<Trial> trials = new LinkedList<>();
        for (int i = 0; i< numTrials; i++){
            trials.add(new RandTrial(generator, size, coords));
        }
        return trials;
    }

    private void addNthGeneration(){
        trials.addAll(createMorphTrials(this));
        trials.addAll(createRandTrials(this, 4, initialSize, initialCoords));
    }

    private List<Trial> createMorphTrials(GA3DBlockGen generator){
        List<Trial> trials = new LinkedList<>();

        stimsToMorph = parentSelector.selectParents(channels, gaName);

        for (Long parentId: stimsToMorph){
            trials.add(new MorphTrial(generator, parentId));
        }

        return trials;
    }

    /**
     * Override TaskToDo for MultiGADbUtil
     */
    @Override
    protected void writeTrials() {
        for (Trial trial : trials) {
            trial.write();
            Long taskId = trial.getTaskId();
            dbUtil.writeTaskToDo(taskId, taskId, -1, gaName, genId);
        }
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
    protected void updateReadyGeneration() {
        getDbUtil().updateReadyGAsAndGenerationsInfo(gaName, genId);
        System.out.println("Done Generating...");
    }

    public void setParentSelector(ParentSelector parentSelector) {
        this.parentSelector = parentSelector;
    }


    private boolean firstGeneration(){
        MultiGaGenerationInfo info = dbUtil.readReadyGAsAndGenerationsInfo();
        Map<String, Long> readyGens = info.getGenIdForGA();
        return readyGens.get(gaName) == 0;
    }

    @Override
    public void tearDown(){
        pngMaker.close();
        trials = new LinkedList<>();
    }

    public MultiGaDbUtil getDbUtil() {
        return dbUtil;
    }


    public void setDbUtil(MultiGaDbUtil dbUtil) {
        this.dbUtil = dbUtil;
    }

    public ParentSelector getParentSelector() {
        return parentSelector;
    }

    public String getGaName() {
        return gaName;
    }

    public void setGaName(String gaName) {
        this.gaName = gaName;
    }
}
