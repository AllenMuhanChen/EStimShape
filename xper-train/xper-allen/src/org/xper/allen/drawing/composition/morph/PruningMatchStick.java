package org.xper.allen.drawing.composition.morph;

import java.util.*;

public class PruningMatchStick extends MorphedMatchStick{

    private MorphedMatchStick matchStickToMorph;

    // Chooses own random components to preserve
    public void genPruningMatchStick(MorphedMatchStick matchStickToMorph, double magnitude, int numPreserve){
        this.matchStickToMorph = matchStickToMorph;

        List<Integer> componentsToMorph = chooseComponentsToMorph(numPreserve);

        // Construct MorphParameters for componentsToMorph
        Map<Integer, ComponentMorphParameters> paramsForComps = new HashMap<>();
        for (Integer comp : componentsToMorph) {
            ComponentMorphParameters params = new ComponentMorphParameters(magnitude);
            paramsForComps.put(comp, params);
        }

        // Call MorphedMatchStick
        genMorphedMatchStick(paramsForComps, this.matchStickToMorph);

    }

    private List<Integer> chooseComponentsToMorph(int numPreserve) {
        List<Integer> componentsToMorph = matchStickToMorph.getCompList();
        Collections.shuffle(componentsToMorph);
        List<Integer> toPreserve = new ArrayList<Integer>();
        for (int i = 0; i< numPreserve; i++){
            toPreserve.add(componentsToMorph.get(i));
        }
        componentsToMorph.removeAll(toPreserve);
        System.err.println("componentsToMorph: " + componentsToMorph.size() + " out of " + matchStickToMorph.getNComponent());
        return componentsToMorph;
    }
}