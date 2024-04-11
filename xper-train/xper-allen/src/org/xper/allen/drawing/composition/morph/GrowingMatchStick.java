package org.xper.allen.drawing.composition.morph;

import org.xper.allen.drawing.ga.RFMatchStick;
import org.xper.allen.drawing.ga.ReceptiveField;

import javax.media.j3d.Morph;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
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
        // Find the current number of components
        HashSet<Integer> componentsToRemove = specifyCompsToRemove(matchStickToMorph);

        MorphedMatchStick removedLimbMatchStick = genRemovedLimbsMatchStick(matchStickToMorph, componentsToRemove);

        Map<Integer, ComponentMorphParameters> paramsForComps = specifyCompMorphParams(removedLimbMatchStick, magnitude);

        // Call MorphedMatchStick
        MorphedMatchStick compMorphedMatchStick = new MorphedMatchStick();
        compMorphedMatchStick.setProperties(getScaleForMAxisShape(), matchStickToMorph.getTextureType());
        compMorphedMatchStick.genMorphedComponentsMatchStick(paramsForComps, removedLimbMatchStick);

    }

    private MorphedMatchStick genRemovedLimbsMatchStick(MorphedMatchStick matchStickToMorph, HashSet<Integer> componentsToRemove) {
        MorphedMatchStick removedLimbMatchStick = new MorphedMatchStick();
        removedLimbMatchStick.setProperties(getScaleForMAxisShape(), matchStickToMorph.getTextureType());
        removedLimbMatchStick.genRemovedLimbsMatchStick(matchStickToMorph, componentsToRemove);
        return removedLimbMatchStick;
    }

    private HashSet<Integer> specifyCompsToRemove(MorphedMatchStick matchStickToMorph) {
        int currentNComp = matchStickToMorph.getNComponent();
        HashSet<Integer> componentsToRemove = new HashSet<>();

        // Find max and min number of components allowed
        int maxNComp = findMaxIndex(PARAM_nCompDist) + 1;
        int minNComp = findMinIndex(PARAM_nCompDist) + 1;

        // Ensure the min and max are within valid range
        if (minNComp < 1) minNComp = 1;
        if (maxNComp > currentNComp) maxNComp = currentNComp;

        // Calculate the number of components to remove based on a simple strategy
        int componentsToRemoveCount = calculateComponentsToRemove(currentNComp, minNComp, maxNComp);
        System.out.println("Removing " + componentsToRemoveCount + " components");
        // Randomly choose components to remove

        while (componentsToRemove.size() < componentsToRemoveCount) {
            int componentId = (int) (Math.random() * currentNComp) + 1; // Assuming component IDs start at 1
            if (matchStickToMorph.getLeafBranch()[componentId]) continue; // Skip if it is a branch
            componentsToRemove.add(componentId);
        }
        return componentsToRemove;
    }

    private int findMaxIndex(double[] array) {
        for (int i = array.length - 1; i >= 0; i--) {
            if (array[i] != 0.0) return i;
        }
        return -1; // Default case, though this should not happen with valid data
    }

    private int findMinIndex(double[] array) {
        for (int i = 0; i < array.length; i++) {
            if (array[i] != 0.0) return i;
        }
        return -1; // Default case, though this should not happen with valid data
    }

    private int calculateComponentsToRemove(int currentNComp, int minNComp, int maxNComp) {
        if (minNComp == maxNComp) return 0; // No removal if min and max are the same
        int range = maxNComp - minNComp;
        return (int) (Math.random() * (range + 1)) + (currentNComp - maxNComp);
    }


    private Map<Integer, ComponentMorphParameters> specifyCompMorphParams(MorphedMatchStick matchStickToMorph, double magnitude) {
        NormalMorphDistributer normalMorphDistributer = new NormalMorphDistributer(sigma);
        // Construct MorphParameters for components
        Map<Integer, ComponentMorphParameters> paramsForComps = new HashMap<Integer, ComponentMorphParameters>();
        for (int i = 1; i<= matchStickToMorph.getNComponent(); i++) {
            ComponentMorphParameters params = new NormalDistributedComponentMorphParameters(magnitude, normalMorphDistributer);
            paramsForComps.put(i, params);
        }
        return paramsForComps;
    }

    public int getMaxTotalAttempts() {
        return MAX_TOTAL_ATTEMPTS;
    }

    public void setMaxTotalAttempts(int maxTotalAttempts) {
        MAX_TOTAL_ATTEMPTS = maxTotalAttempts;
    }
}