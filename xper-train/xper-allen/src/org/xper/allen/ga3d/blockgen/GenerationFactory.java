package org.xper.allen.ga3d.blockgen;

import org.xper.allen.Trial;

import javax.media.j3d.Link;
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
    int numTrials=40;

    public GenerationFactory(int numTrials) {
        this.numTrials = numTrials;
    }

    public List<Trial> createFirstGenerationTrials(){
        List<Trial> trials = new LinkedList<>();
        for (int i=0; i<numTrials; i++){
            trials.add(new RandTrial());
        }
        return trials;
    }

//    public List<Trial> createNthGenerationTrials(){
//        List<Trial> trials = new LinkedList<>();
//
////        List<Long> stimObjIds = parentSelector.selectParents();
//    }
}
