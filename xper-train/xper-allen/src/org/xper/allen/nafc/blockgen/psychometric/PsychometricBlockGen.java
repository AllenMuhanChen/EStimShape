package org.xper.allen.nafc.blockgen.psychometric;

import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

import org.xper.Dependency;
import org.xper.allen.drawing.composition.qualitativemorphs.PsychometricQualitativeMorphParameterGenerator;
import org.xper.allen.nafc.blockgen.PsychometricTrialListFactory;
import org.xper.allen.nafc.blockgen.Trial;
import org.xper.allen.nafc.blockgen.rand.RandFactoryParameters;
import org.xper.allen.nafc.blockgen.rand.RandTrialListFactory;
import org.xper.exception.VariableNotFoundException;

public class PsychometricBlockGen extends AbstractPsychometricTrialGenerator {

    Long genId;
	private List<Trial> trials = new LinkedList<>();
    private PsychometricFactoryParameters psychometricFactoryParameters;
    private RandFactoryParameters randFactoryParameters;


    public void setUp(PsychometricFactoryParameters psychometricFactoryParameters,
                      RandFactoryParameters randFactoryParameters){
        this.psychometricFactoryParameters = psychometricFactoryParameters;
        this.randFactoryParameters = randFactoryParameters;
    }

    @Override
    public void generate() {
        addPsychometricTrials(psychometricFactoryParameters);
        addRandTrials(randFactoryParameters);
        preWriteTrials();
        shuffleTrials();
        updateGenId();
        writeTrials();
        dbUtil.updateReadyGenerationInfo(genId, trials.size());
        System.out.println("Done Generating...");
        pngMaker.close();
    }

    private void addPsychometricTrials(PsychometricFactoryParameters psychometricFactoryParameters) {
        PsychometricTrialListFactory psychometricFactory = new PsychometricTrialListFactory(
                this, psychometricFactoryParameters
        );
        trials.addAll(psychometricFactory.createTrials());
    }

    private void addRandTrials(RandFactoryParameters randFactoryParameters) {
        RandTrialListFactory randFactory = new RandTrialListFactory(
        this, randFactoryParameters);
        trials.addAll(randFactory.createTrials());
    }

    private void preWriteTrials() {
        for(Trial trial:trials){
            trial.preWrite();
        }
    }

    private void shuffleTrials() {
        Collections.shuffle(trials);
    }

    private void updateGenId() {
        try {
            /**
             * Gen ID is important for xper to be able to load new tasks on the fly. It will only do so if the generation Id is upticked.
             */
            genId = dbUtil.readReadyGenerationInfo().getGenId() + 1;
        } catch (VariableNotFoundException e) {
            dbUtil.writeReadyGenerationInfo(0, 0);
        }
    }

    private void writeTrials() {
        for (Trial trial : trials) {
            trial.write();
            Long taskId = trial.getTaskId();
            dbUtil.writeTaskToDo(taskId, taskId, -1, genId);
        }
    }

    public String getGeneratorPngPath() {
        return generatorPngPath;
    }

    public void setGeneratorPngPath(String generatorPngPath) {
        this.generatorPngPath = generatorPngPath;
    }

    public String getExperimentPngPath() {
        return experimentPngPath;
    }

    public void setExperimentPngPath(String experimentPngPath) {
        this.experimentPngPath = experimentPngPath;
    }

    public String getGeneratorSpecPath() {
        return generatorSpecPath;
    }

    public void setGeneratorSpecPath(String generatorSpecPath) {
        this.generatorSpecPath = generatorSpecPath;
    }


}
