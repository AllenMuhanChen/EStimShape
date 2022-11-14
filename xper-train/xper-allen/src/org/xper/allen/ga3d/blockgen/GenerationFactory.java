package org.xper.allen.ga3d.blockgen;

import org.xper.Dependency;
import org.xper.allen.Trial;
import org.xper.allen.ga.ParentSelector;

import java.util.LinkedList;
import java.util.List;

/**
 * Will control the proportion of trial types.
 * 32/40: morphTrial
 *      6 from top 10%
 *      4 from next 20%
 *      3 from next 20%
 *      2 from next 20%
 *      1 from bottom 10%
 *
 * We're going to have to think about how we're going to handle lineages inside of here
 *
 *
 */
public class GenerationFactory {

    @Dependency
    ParentSelector parentSelector;

    private final GA3DBlockGen generator;

    int numTrials=40;

    public GenerationFactory(GA3DBlockGen generator, int numTrials) {
        this.generator = generator;
        this.numTrials = numTrials;
    }

    public List<Trial> createFirstGenerationTrials(){
        List<Trial> trials = new LinkedList<>();
        for (int i=0; i<numTrials; i++){
            trials.add(new RandTrial(generator));
        }
        return trials;
    }

    public List<Trial> createNthGenerationTrials(){
        List<Trial> trials = new LinkedList<>();

        List<Long> stimObjIds = parentSelector.selectParents();

        for (Long stimObjId: stimObjIds){
            trials.add(new MorphTrial(generator, stimObjId));
        }

        return trials;
    }
}
