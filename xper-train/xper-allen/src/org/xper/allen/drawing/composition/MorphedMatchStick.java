package org.xper.allen.drawing.composition;

import org.xper.allen.drawing.composition.morph.ComponentMorphParameters;
import org.xper.allen.drawing.composition.morph.MorphedMAxisArc;
import org.xper.drawing.stick.JuncPt_struct;

import java.util.Map;
import java.util.function.BiConsumer;
import java.util.function.Consumer;

public class MorphedMatchStick extends AllenMatchStick{
    public static final int NUM_ATTEMPTS_PER_COMPONENT = 15;
    private static final int NUM_ATTEMPTS_PER_ARC = 100;

    public void genMorphedMatchStick(Map<Integer, ComponentMorphParameters> morphParametersForComponents, MorphedMatchStick matchStickToMorph){
        MorphedMatchStick backup = new MorphedMatchStick();
        backup.copyFrom(matchStickToMorph);

        // Attempt to morph every component. If we fail, then restart with the backup.
        while (true) {
            try {
                morphAllComponents(morphParametersForComponents, matchStickToMorph);
                positionShape();
                attemptSmoothizeMStick();
                break;
            } catch (MorphException e) {
                cleanData();
                copyFrom(backup);
                e.printStackTrace();
                System.err.println("Failed to morph matchstick. Retrying...");
            }
        }
    }

    private void attemptSmoothizeMStick() {
        boolean success = false;
        if(success){
            boolean res;
            try{
                res = smoothizeMStick();
            } catch(Exception e){
                throw new RuntimeException("Failed to smoothize the matchstick!");
            }
            if(!res){
                throw new RuntimeException("Failed to smoothize the matchstick!");
            }
        }
    }

    private void morphAllComponents(Map<Integer, ComponentMorphParameters> morphParametersForComponents, MorphedMatchStick matchStickToMorph) {
        morphParametersForComponents.forEach(new BiConsumer<Integer, ComponentMorphParameters>() {
            @Override
            public void accept(Integer componentIndex, ComponentMorphParameters morphParams) {
                attemptToMorphComponent(componentIndex, morphParams, matchStickToMorph);
            }
        });
    }

    private void attemptToMorphComponent(Integer componentIndex, ComponentMorphParameters morphParams, MorphedMatchStick matchStickToMorph) {
        MorphedMatchStick localBackup = new MorphedMatchStick();
        localBackup.copyFrom(matchStickToMorph);

        int numAttempts=0;
        while (numAttempts < NUM_ATTEMPTS_PER_COMPONENT) {
            try {
                morphComponent(componentIndex, morphParams);
                return;
            } catch (MorphException e) {
                e.printStackTrace();
                System.err.println("Failed to Morph Component " + componentIndex + " with parameters " + morphParams);
                System.err.println("Retrying...");
                System.err.println("Attempt " + numAttempts + " of " + NUM_ATTEMPTS_PER_COMPONENT);
                matchStickToMorph.copyFrom(localBackup);
            } finally {
                numAttempts++;
            }
        }
        throw new MorphException("Did not successfully morph component " + componentIndex + " after " + NUM_ATTEMPTS_PER_COMPONENT + " attempts.");
    }

    private void morphComponent(int id, ComponentMorphParameters morphParams) throws MorphException{
        int[] compLabel = MutationSUB_compRelation2Target(id);
        MorphedMAxisArc newArc;
        while (true){
            while(true){
                attemptToGenerateValidMorphedArc(id, morphParams);
                // Update JuncPts using new Arc

                // Update Skeleton info (Comps) and check for collisions
                break;
            }

            // Update EndPt and JuncPt structs using new Comp() skeleton

            // Update Radii

            // Final checks (tube collision and validMStickSize)

            break;
        }



    }

    private void attemptToGenerateValidMorphedArc(int id, ComponentMorphParameters morphParams) {
        MorphedMAxisArc newArc;
        MorphedMatchStick backup = new MorphedMatchStick();
        backup.copyFrom(this);
        int numAttemptsToGenerateArc = 0;
        while(true){
            try {
                newArc = generateMorphedArc(id, morphParams);
                checkJunctions();
                break;
            } catch (MorphException e){
                copyFrom(backup);
            } finally {
                numAttemptsToGenerateArc++;
            }
            if(numAttemptsToGenerateArc > NUM_ATTEMPTS_PER_ARC){
                throw new MorphException("Failed to generate a valid morphed arc after " + NUM_ATTEMPTS_PER_COMPONENT + " attempts.");
            }
        }
    }

    private void checkJunctions() throws MorphException{

    }

    private MorphedMAxisArc generateMorphedArc(int id, ComponentMorphParameters morphParams) {
        MorphedMAxisArc arcToMorph = new MorphedMAxisArc(getComp()[id].getmAxisInfo());
        int alignedPt = MutationSUB_determineHinge(id);
        MorphedMAxisArc newArc = new MorphedMAxisArc();
        newArc.genMorphedArc(arcToMorph, alignedPt, morphParams);
        return newArc;
    }

    protected void forEachJunctionOf(int id, Consumer<JuncPt_struct> junctionConsumer) {
        for (int i = 1; i<= getnJuncPt(); i++) {
            for (int j = 1; j <= getJuncPt()[i].getnComp(); j++){
                if (getJuncPt()[i].getComp()[j] == id) {
                    junctionConsumer.accept(getJuncPt()[i]);
                }
            }
        }
    }

    public static class MorphException extends RuntimeException{
        public MorphException(String message){
            super(message);
        }
    }

}