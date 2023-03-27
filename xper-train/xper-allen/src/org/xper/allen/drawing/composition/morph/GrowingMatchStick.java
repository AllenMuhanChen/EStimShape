package org.xper.allen.drawing.composition.morph;

import java.util.HashMap;
import java.util.Map;

public class GrowingMatchStick extends MorphedMatchStick{

    public void genGrowingMatchStick(MorphedMatchStick matchStickToMorph, double magnitude) {

        // Construct MorphParameters for components
        Map<Integer, ComponentMorphParameters> paramsForComps = new HashMap<Integer, ComponentMorphParameters>();
        for (int i=1; i<=matchStickToMorph.getNComponent(); i++) {
            ComponentMorphParameters params = new ComponentMorphParameters(magnitude);
            paramsForComps.put(i, params);
        }


        // Call MorphedMatchStick
        genMorphedMatchStick(paramsForComps, matchStickToMorph);

    }
}