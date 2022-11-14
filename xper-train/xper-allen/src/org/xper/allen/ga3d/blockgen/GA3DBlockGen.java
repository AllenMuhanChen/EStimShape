package org.xper.allen.ga3d.blockgen;

import org.xper.Dependency;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.Trial;

import java.util.LinkedList;
import java.util.List;

public class GA3DBlockGen extends AbstractMStickPngTrialGenerator {
    Long genId;
    String gaName;

    private List<Trial> trials = new LinkedList<>();

    @Dependency
    GenerationFactory factory = new GenerationFactory(this, 40);

    @Override
    protected void addTrials() {
        if(firstGeneration()){
            addFirstGeneration();
        } else{
            addNthGeneration();
            //add:
            // 1. Compile neural responses then choose stimuli to morph
            // 2. Assign stimulus type (rand, or child)
        }
    }

    private boolean firstGeneration(){
        return genId == 0;
    }

    private void addFirstGeneration(){
        trials.addAll(factory.createFirstGenerationTrials());
    }

    private void addNthGeneration(){
        trials.addAll(factory.createNthGenerationTrials());
    }

}
