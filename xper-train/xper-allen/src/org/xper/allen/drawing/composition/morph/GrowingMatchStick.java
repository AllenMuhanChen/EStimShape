package org.xper.allen.drawing.composition.morph;

import org.xper.allen.drawing.ga.RFMatchStick;
import org.xper.allen.drawing.ga.ReceptiveField;

import java.util.HashMap;
import java.util.Map;

public class GrowingMatchStick extends RFMatchStick {
    protected static int MAX_TOTAL_ATTEMPTS = 10;

    private double sigma;

    public GrowingMatchStick(double sigma) {
        this.sigma = sigma;
    }

    public GrowingMatchStick() {
        this.sigma = 1/3.0;
    }

    public GrowingMatchStick(ReceptiveField rf, double sigma) {
        super(rf);
        this.sigma = sigma;
    }

    public GrowingMatchStick(ReceptiveField rf) {
        super(rf);
        this.sigma = 1/3.0;
    }

    public void genGrowingMatchStick(MorphedMatchStick matchStickToMorph, double magnitude) {


        NormalMorphDistributer normalMorphDistributer = new NormalMorphDistributer(sigma);
        // Construct MorphParameters for components
        Map<Integer, ComponentMorphParameters> paramsForComps = new HashMap<Integer, ComponentMorphParameters>();
        for (int i=1; i<=matchStickToMorph.getNComponent(); i++) {
            ComponentMorphParameters params = new NormalDistributedComponentMorphParameters(magnitude, normalMorphDistributer);
            paramsForComps.put(i, params);
        }


        // Call MorphedMatchStick
        genMorphedComponentsMatchStick(paramsForComps, matchStickToMorph);

    }

    public int getMaxTotalAttempts() {
        return MAX_TOTAL_ATTEMPTS;
    }

    public void setMaxTotalAttempts(int maxTotalAttempts) {
        MAX_TOTAL_ATTEMPTS = maxTotalAttempts;
    }
}