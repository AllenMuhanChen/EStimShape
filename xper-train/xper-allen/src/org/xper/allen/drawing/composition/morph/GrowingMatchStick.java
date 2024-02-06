package org.xper.allen.drawing.composition.morph;

import org.xper.allen.drawing.ga.RFMatchStick;

import java.util.HashMap;
import java.util.Map;

public class GrowingMatchStick extends RFMatchStick {

    private double sigma;

    public GrowingMatchStick(double sigma) {
        this.sigma = sigma;
    }

    public GrowingMatchStick() {
        this.sigma = 1/3.0;
    }

    public void genGrowingMatchStick(MorphedMatchStick matchStickToMorph, double magnitude) {
        NormalMorphDistributer normalMorphDistributer = new NormalMorphDistributer(sigma);
        // Construct MorphParameters for components
        Map<Integer, ComponentMorphParameters> paramsForComps = new HashMap<Integer, ComponentMorphParameters>();
        for (int i=1; i<=matchStickToMorph.getNComponent(); i++) {
            ComponentMorphParameters params = new ComponentMorphParameters(magnitude, normalMorphDistributer);
            paramsForComps.put(i, params);
        }


        // Call MorphedMatchStick
        genMorphedMatchStick(paramsForComps, matchStickToMorph);

    }
}