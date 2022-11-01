package org.xper.allen.nafc.blockgen.ga;

import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.nafc.blockgen.Trial;
import org.xper.allen.nafc.blockgen.psychometric.AbstractPsychometricTrialGenerator;

import java.util.LinkedList;
import java.util.List;

public class GA3DBlockGen extends AbstractMStickPngTrialGenerator {
    Long genId;
    private List<Trial> trials = new LinkedList<>();

    public void generate(){
        pngMaker.createDrawerWindow();

        if(firstGeneration()){
            addFirstGeneration();
        } else{
            addNthGeneration();
            //add:
            // 1. Compile neural responses then choose stimuli to morph
            // 2. Assign stimulus type (rand, or child)
        }
        preWriteTrials();
        shuffleTrials();

        if(firstGeneration()){
            writeFirstGeneration();
        } else{
            writeNthGeneration();
        }

        dbUtil.updateReadyGenerationInfo(genId, trials.size());
        System.out.println("Done Generating...");
        pngMaker.close();

    }

}
