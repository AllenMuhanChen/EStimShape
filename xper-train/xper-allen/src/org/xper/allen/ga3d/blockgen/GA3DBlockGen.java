package org.xper.allen.ga3d.blockgen;

import org.xper.Dependency;
import org.xper.allen.ga.MultiGaGenerationInfo;
import org.xper.allen.ga.ParentSelector;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.Trial;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.drawing.Coordinates2D;

import java.util.*;
import java.util.function.BiConsumer;

public class GA3DBlockGen extends AbstractMStickPngTrialGenerator {

    @Dependency
    MultiGaDbUtil dbUtil;
    @Dependency
    ParentSelector parentSelector;
    @Dependency
    Integer numLineages;

    private String gaBaseName;
    private Map<String, List<Trial>> trialsForGA = new LinkedHashMap<String, List<Trial>>();
    private Map<String, Long> genIdsForGA = new LinkedHashMap<String, Long>();
    private double initialSize;
    private Coordinates2D initialCoords;
    private int numTrials;
    protected List<String> channels;

    private List<Long> stimsToMorph;
    private List<String> gaNames = new LinkedList<>();

    /**
     * @param numTrials - number of trials per lineage
     * @param initialSize - initial size of stimuli in GA
     * @param initialCoords - initial coordinates of stimuli in GA
     * @param channels - list of channels to analyze for parent selection
     */
    public void setUp(int numTrials, double initialSize, Coordinates2D initialCoords, List<String> channels){
        this.numTrials = numTrials;
        this.initialSize = initialSize;
        this.initialCoords = initialCoords;
        this.gaBaseName = "3D";
        this.channels = channels;

        //Populate gaNames based off number of lineages. i.e "3D-1", "3D-2", etc.
        this.gaNames = getGaNames();

        //Populate trials_for_ga with empty lists
        for (String gaName : gaNames){
            trialsForGA.put(gaName, new LinkedList<Trial>());
        }

    }

    public List<String> getGaNames() {
        List<String> gaNames = new LinkedList<>();
        for (int i = 1; i <= numLineages; i++){
            gaNames.add(gaBaseName + "-" + i);
        }
        return gaNames;
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
        trialsForGA.get(gaName).addAll(createRandTrials(this, numTrials, initialSize, initialCoords));
    }

    private List<Trial> createMorphTrials(GA3DBlockGen generator, String gaName){
        List<Trial> trials = new LinkedList<>();

        stimsToMorph = parentSelector.selectParents(gaName);

        for (Long parentId: stimsToMorph){
            trials.add(new MorphTrial(generator, gaName, parentId));
        }

        return trials;
    }


    private List<Trial> createRandTrials(GA3DBlockGen generator, int numTrials, double size, Coordinates2D coords){
        List<Trial> trials = new LinkedList<>();
        for (int i = 0; i< numTrials; i++){
            trials.add(new RandTrial(generator, size, coords));
        }
        return trials;
    }

    private void addNthGeneration(String gaName){
        trialsForGA.get(gaName).addAll(createMorphTrials(this, gaName));
        trialsForGA.get(gaName).addAll(createRandTrials(this, 4, initialSize, initialCoords));
    }


    @Override
    protected void shuffleTrials() {
        trialsForGA.forEach(new BiConsumer<String, List<Trial>>() {
            @Override
            public void accept(String gaName, List<Trial> trials) {
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
//                getDbUtil().writeReadyGenerationInfo(0, 0);
            }
            genIdsForGA.put(gaName, genId);
        }
    }

    /**
     * Override TaskToDo for MultiGADbUtil
     */
    @Override
    protected void writeTrials() {
        trialsForGA.forEach(new BiConsumer<String, List<Trial>>() {
            @Override
            public void accept(String gaName, List<Trial> trials) {
                for (Trial trial : trials) {
                    trial.write();
                    Long taskId = trial.getTaskId();
                    dbUtil.writeTaskToDo(taskId, taskId, -1, gaName, genIdsForGA.get(gaName));
                }
            }
        });

    }

    @Override
    protected void updateReadyGeneration() {
        for (String gaName : gaNames){
            getDbUtil().updateReadyGAsAndGenerationsInfo(gaName, genIdsForGA.get(gaName));
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
        trialsForGA = new LinkedHashMap<String, List<Trial>>();
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
        return gaBaseName;
    }

    public void setGaBaseName(String gaBaseName) {
        this.gaBaseName = gaBaseName;
    }

    public Integer getNumLineages() {
        return numLineages;
    }

    public void setNumLineages(Integer numLineages) {
        this.numLineages = numLineages;
    }
}