package org.xper.allen.ga3d.blockgen;

import org.xper.Dependency;
import org.xper.allen.ga.MultiGaGenerationInfo;
import org.xper.allen.ga.ParentSelector;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.drawing.Coordinates2D;

import java.util.*;
import java.util.function.BiConsumer;

/**
 * Implements lineages as a list of separate GA's.
 * i.e
 * Lineage 1: "GA-1"
 * Lineage 2: "GA-2"
 */
public class GA3DLineageBlockGenerator extends GABlockGenerator {

    @Dependency
    ParentSelector parentSelector;
    @Dependency
    Integer numLineages;

    private Map<String, List<ThreeDGAStim>> trialsForGA = new LinkedHashMap<String, List<ThreeDGAStim>>();
    private Map<String, Long> genIdForGA = new LinkedHashMap<String, Long>();
    private double initialSize;
    private Coordinates2D initialCoords;
    private int numStimuli;
    protected List<String> channels;

    private List<Long> stimsToMorph;
    private List<String> gaNames = new LinkedList<>();

    /**
     * @param numStimuli - number of trials per lineage
     * @param initialSize - initial size of stimuli in GA
     * @param initialCoords - initial coordinates of stimuli in GA
     * @param channels - list of channels to analyze for parent selection
     */
    public void setUp(int numStimuli, int numTrialsPerStimuli, double initialSize, Coordinates2D initialCoords, List<String> channels){
        this.numStimuli = numStimuli;
        this.numTrialsPerStimuli = numTrialsPerStimuli;
        this.initialSize = initialSize;
        this.initialCoords = initialCoords;
        this.GA_NAME = "3D";
        this.channels = channels;

        //Populate gaNames based off number of lineages. i.e "3D-1", "3D-2", etc.
        this.gaNames = getGaNames();

        //Populate trials_for_ga with empty lists
        for (String gaName : gaNames){
            trialsForGA.put(gaName, new LinkedList<ThreeDGAStim>());
        }

    }

    public List<String> getGaNames() {
        List<String> gaLineageNames = new LinkedList<>();
        for (int i = 1; i <= numLineages; i++){
            gaLineageNames.add(GA_NAME + "-" + i);
        }
        return gaLineageNames;
    }

    @Override
    protected void addTrials() {
        for (String gaName : gaNames) {
            if (isFirstGeneration(gaName)) {
                addFirstGeneration(gaName);
            } else {
                addNthGeneration(gaName);
            }
        }

    }

    private void addFirstGeneration(String gaName){
        trialsForGA.get(gaName).addAll(createRandTrials(this, numStimuli, initialSize, initialCoords));
    }

    private List<ThreeDGAStim> createMorphTrials(GA3DLineageBlockGenerator generator, String gaName){
        List<ThreeDGAStim> trials = new LinkedList<>();

        stimsToMorph = parentSelector.selectParents(gaName);

        for (Long parentId: stimsToMorph){
            trials.add(new MorphStim(generator, gaName, parentId));
        }

        return trials;
    }


    private List<ThreeDGAStim> createRandTrials(GA3DLineageBlockGenerator generator, int numTrials, double size, Coordinates2D coords){
        List<ThreeDGAStim> trials = new LinkedList<>();
        for (int i = 0; i< numTrials; i++){
            trials.add(new RandStim(generator, size, coords));
        }
        return trials;
    }

    private void addNthGeneration(String gaName){
        trialsForGA.get(gaName).addAll(createMorphTrials(this, gaName));
        trialsForGA.get(gaName).addAll(createRandTrials(this, 4, initialSize, initialCoords));
    }


    @Override
    protected void shuffleTrials() {
        trialsForGA.forEach(new BiConsumer<String, List<ThreeDGAStim>>() {
            @Override
            public void accept(String gaName, List<ThreeDGAStim> trials) {
                Collections.shuffle(trials);
            }
        });
    }

    @Override
    protected void updateGenId() {
        for (String gaName : gaNames){
            Long genId;
            try {
                genId = getDbUtil().readMultiGAReadyGenerationInfo().getGenIdForGA(gaName) + 1;
            } catch (Exception e) {
                getDbUtil().writeReadyGAsAndGenerationsInfo(gaNames);
                genId = 0L;
            }
            genIdForGA.put(gaName, genId);
        }
    }

    /**
     * Override TaskToDo for MultiGADbUtil
     */
    @Override
    protected void writeTrials() {
        trialsForGA.forEach(new BiConsumer<String, List<ThreeDGAStim>>() {
            @Override
            public void accept(String gaName, List<ThreeDGAStim> trials) {
                for (ThreeDGAStim trial : trials) {
                    trial.writeStim();
                    trial.writeGaInfo(gaName, genIdForGA.get(gaName));
                    Long stimId = trial.getStimId();
                    for (int i = 0; i < numTrialsPerStimuli; i++) {
                        long taskId = getGlobalTimeUtil().currentTimeMicros();
                        dbUtil.writeTaskToDo(taskId, stimId, -1, gaName, genIdForGA.get(gaName));
                    }
                }
            }
        });

    }

    @Override
    protected void updateReadyGeneration() {
        for (String gaName : gaNames){
            getDbUtil().updateReadyGAsAndGenerationsInfo(gaName, genIdForGA.get(gaName));
        }

        System.out.println("Done Generating...");
    }

    public void setParentSelector(ParentSelector parentSelector) {
        this.parentSelector = parentSelector;
    }


    private boolean isFirstGeneration(String gaName){
        MultiGaGenerationInfo info = dbUtil.readReadyGAsAndGenerationsInfo();
        Map<String, Long> readyGens = info.getGenIdForGA();

        return readyGens.getOrDefault(gaName,0L) == 0;
    }

    @Override
    public void tearDown(){
        pngMaker.close();
        stims = new LinkedList<>();
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

    public String getGaBaseName() {
        return GA_NAME;
    }

    public void setGaBaseName(String gaBaseName) {
        this.GA_NAME = gaBaseName;
    }

    public Integer getNumLineages() {
        return numLineages;
    }

    public void setNumLineages(Integer numLineages) {
        this.numLineages = numLineages;
    }
}