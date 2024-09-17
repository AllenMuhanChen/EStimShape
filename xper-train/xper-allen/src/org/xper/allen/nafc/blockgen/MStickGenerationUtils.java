package org.xper.allen.nafc.blockgen;

import org.xper.allen.drawing.composition.experiment.EStimShapeTwoByTwoMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.nafc.blockgen.estimshape.StickProvider;

public class MStickGenerationUtils {
    public static EStimShapeTwoByTwoMatchStick attemptMorph(StickProvider<EStimShapeTwoByTwoMatchStick> provider, int maxAttempts) throws ProceduralMatchStick.MorphRepetitionException {
        int nAttempts = 0;
        while (nAttempts < maxAttempts){
            try {
                System.out.println("Attempting Morph " + nAttempts + " of " + maxAttempts);
                System.out.println("In line: " + Thread.currentThread().getStackTrace()[2].getLineNumber() + " of file: " + Thread.currentThread().getStackTrace()[2].getFileName());
                return provider.makeStick();
            } catch (MorphedMatchStick.MorphException me){
                System.out.println("Failed Morph: because of reason");
                System.err.println(me.getMessage());
                System.out.println("In line: " + Thread.currentThread().getStackTrace()[2].getLineNumber() + " of file: " + Thread.currentThread().getStackTrace()[2].getFileName());

            }
            nAttempts++;
        }
        throw new MorphedMatchStick.MorphException("Could not morph after " + maxAttempts + " attempts");
    }
}