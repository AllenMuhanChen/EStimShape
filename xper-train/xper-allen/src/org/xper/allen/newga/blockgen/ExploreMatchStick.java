package org.xper.allen.newga.blockgen;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.morph.ComponentMorphParameters;
import org.xper.allen.drawing.composition.morph.MorphDistributer;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.drawing.composition.morph.PruningMatchStick;
import org.xper.allen.drawing.composition.morph.PruningMatchStick.PruningMStickData;

import java.util.HashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;

public class ExploreMatchStick extends MorphedMatchStick {

    private final List<Integer> componentsToMorph;
    PruningMatchStick parentMStick;

    public ExploreMatchStick(PruningMatchStick parentMStick, List<Integer> componentsToMorph) {
        this.parentMStick = parentMStick;
        if (componentsToMorph == null) {
            componentsToMorph = new LinkedList<>();
        }
        this.componentsToMorph = componentsToMorph;
    }

    public void genExploreMatchStick(double magnitude) {
        // Construct MorphParameters for componentsToMorph
        Map<Integer, ComponentMorphParameters> paramsForComps = new HashMap<>();
        for (Integer comp : componentsToMorph) {
            ComponentMorphParameters params = new ComponentMorphParameters(magnitude, new MorphDistributer(1.0));
            paramsForComps.put(comp, params);
        }

        // Call MorphedMatchStick
        genMorphedMatchStick(paramsForComps, parentMStick);
    }

    @Override
    public ExploreMStickData getMStickData(){
        AllenMStickData superData = super.getMStickData();

        return new ExploreMStickData(superData, componentsToMorph);

    }

}