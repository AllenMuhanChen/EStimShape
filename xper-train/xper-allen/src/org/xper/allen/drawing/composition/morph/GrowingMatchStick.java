package org.xper.allen.drawing.composition.morph;

import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.pga.RFStrategy;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;

public class GrowingMatchStick extends GAMatchStick {
    protected static int MAX_TOTAL_ATTEMPTS = 10;

    private double sigma;

    public GrowingMatchStick(double sigma) {
        this.sigma = sigma;
    }


    public GrowingMatchStick(ReceptiveField rf, double sigma, RFStrategy rfStrategy, String textureType1) {
        super(rf, rfStrategy);
        this.sigma = sigma;
    }

    public GrowingMatchStick(ReceptiveField rf, RFStrategy rfStrategy) {
        this(rf, 1/3.0, rfStrategy, "SHADE");
    }

    private MorphedMatchStick genComponentMorphMatchStick(MorphedMatchStick matchStickToMorph, Map<Integer, ComponentMorphParameters> paramsForComps, MorphedMatchStick removedLimbMatchStick) {
        MorphedMatchStick compMorphedMatchStick = new MorphedMatchStick();
        compMorphedMatchStick.setProperties(getScaleForMAxisShape(), matchStickToMorph.getTextureType(), 1.0);
        compMorphedMatchStick.genMorphedComponentsMatchStick(paramsForComps, removedLimbMatchStick, true);
        return compMorphedMatchStick;
    }

    public void genGrowingMatchStick(MorphedMatchStick matchStickToMorph, double magnitude) {
        if (rfStrategy.equals(RFStrategy.COMPLETELY_INSIDE)) {
            //Removing Comps - Non RF operation
            HashSet<Integer> componentsToRemove = specifyCompsToRemove(matchStickToMorph, magnitude);
            MorphedMatchStick removedLimbMatchStick = genRemovedLimbsMatchStick(matchStickToMorph, componentsToRemove);

            //Morphing Existing Comps - Either NON RF or RF Operation
            Map<Integer, ComponentMorphParameters> paramsForComps = specifyCompMorphParams(removedLimbMatchStick, magnitude, sigma);
            MorphedMatchStick compMorphedMatchStick = genComponentMorphMatchStick(matchStickToMorph, paramsForComps, removedLimbMatchStick);

            //Adding New Comps - NON RF Operation
            int nCompsToAdd = specifyNCompsToAdd(compMorphedMatchStick, magnitude);
            genAddedLimbsMatchStick(compMorphedMatchStick, nCompsToAdd);
        } else {
            boolean morphEntireShape = false;
            //based on magnitude, determine if morphing should impact both inside and outside of RF
            if (Math.random() < magnitude) {
                morphEntireShape = true;
            }

            boolean morphInsideRF = false;
            boolean morphOutsideRF = false;

            //if morphing the entire shape, morph both inside and outside of RF
            if (morphEntireShape) {
                morphInsideRF = true;
                morphOutsideRF = true;
            } else {
                //if not morphing the entire shape, randomly determine if morphing should impact inside or outside of RF
                if (Math.random() < 0.5) {
                    morphInsideRF = true;
                } else {
                    morphOutsideRF = true;
                }
            }


            if (morphOutsideRF && !morphInsideRF){
                System.out.println("Morphing outside RF");
                genOutsideRFMorphedMStick(matchStickToMorph, magnitude);
            }
            if (morphInsideRF && !morphOutsideRF) {
                System.out.println("Morphing inside RF");
                genInsideRFMorphedMStick(matchStickToMorph, magnitude);
            }
            if (morphOutsideRF && morphInsideRF) {
                System.out.println("Morphing both inside and outside RF");
                genOutsideRFMorphedMStick(matchStickToMorph, magnitude);
                genInsideRFMorphedMStick(this, magnitude);
            }


        }
    }

    public void genInsideRFMorphedMStick(MorphedMatchStick matchStickToMorph, double magnitude) {
        int numAttempts = 0;
        while (numAttempts < getMaxTotalAttempts()) {
            try {
                numAttempts++;
                //Morphing Existing Comps - Either NON RF or RF Operation
                //TODO: change this to not effect inside RF component
                Map<Integer, ComponentMorphParameters> paramsForComps = specifyInsideRFCompMorphParams(matchStickToMorph, magnitude);
                MorphedMatchStick compMorphedMatchstick = genComponentMorphMatchStick(matchStickToMorph, paramsForComps, matchStickToMorph);
                copyFrom(compMorphedMatchstick);
                positionShape();
                return;
            } catch (MorphedMatchStick.MorphException me) {
                System.err.println(me.getMessage());
                System.out.println("Morphing failed, trying again with new parameters");
            }
        }
        if (numAttempts == getMaxTotalAttempts()) {
            throw new MorphException("Could not generate inside rf morphed matchstick after " + getMaxTotalAttempts() + " attempts");
        }
    }

    public void genOutsideRFMorphedMStick(MorphedMatchStick matchStickToMorph, double magnitude) {
        int numAttempts = 0;
        while (numAttempts < getMaxTotalAttempts()) {
            numAttempts++;
            try {
                //Removing Comps - Non RF operation
                HashSet<Integer> componentsToRemove = specifyCompsToRemove(matchStickToMorph, magnitude);
                MorphedMatchStick removedLimbMatchStick = genRemovedLimbsMatchStick(matchStickToMorph, componentsToRemove);

                //Morphing Existing Comps - NON RF
                //TODO: change this to not effect inside RF component
                Map<Integer, ComponentMorphParameters> paramsForComps = specifyOutsideRFCompMorphParams(removedLimbMatchStick, magnitude);
                MorphedMatchStick compMorphedMatchStick = genComponentMorphMatchStick(matchStickToMorph, paramsForComps, removedLimbMatchStick);

                //Adding New Comps - NON RF Operation
                int nCompsToAdd = specifyNCompsToAdd(compMorphedMatchStick, magnitude);
                genAddedLimbsMatchStick(compMorphedMatchStick, nCompsToAdd);
                positionShape();
            } catch (MorphedMatchStick.MorphException me) {
                System.err.println(me.getMessage());
                continue;
            }
            break;
        }
        if (numAttempts == getMaxTotalAttempts()) {
            throw new MorphException("Could not generate outside rf morphed matchstick after " + getMaxTotalAttempts() + " attempts");
        }
    }

    private int specifyNCompsToAdd(MorphedMatchStick matchStickToMorph, double magnitude) {
        int currentNComp = matchStickToMorph.getNComponent();

        // Find max and min number of components allowed
        int maxNComp = findMaxIndex(PARAM_nCompDist) + 1;
        int minNComp = findMinIndex(PARAM_nCompDist) + 1;

        // Ensure the min and max are within valid range
        if (minNComp < 1) minNComp = 1;
        if (maxNComp < currentNComp) maxNComp = currentNComp; // Adjusted for adding components

        // Determine the maximum number of components that can be added
        int maxComponentsToAdd = maxNComp - currentNComp;

        // If the current number of components is already at or above the max, no components can be added
        if (maxComponentsToAdd <= 0) {
            System.out.println("No components can be added");
            return 0;
        }

        // Calculate the number of components to add
        // For simplicity, let's assume we always aim to add components up to the max,
        // but this logic can be adjusted based on specific needs or distribution patterns.
        int componentsToAdd = calculateNComponentsToAdd(currentNComp, maxNComp, minNComp, magnitude);

        System.out.println("Adding " + componentsToAdd + " components");
        return componentsToAdd;
    }

    // Helper method to calculate the number of components to add
    public static int calculateNComponentsToAdd(int currentNComp, int maxNComp, int minNComp, double magnitude) {
        if (minNComp == maxNComp) return 0; // No addition if min and max are the same
        if (currentNComp >= maxNComp) return 0; // No addition if current is at or above max
        if (Math.random() < magnitude)
            return 1;
        else
            return 0;
//        int targetNComp = (int) (Math.random() * (maxNComp - currentNComp + 1)) + currentNComp;
//        return Math.max(minNComp - currentNComp, targetNComp - currentNComp);
    }

    private MorphedMatchStick genRemovedLimbsMatchStick(MorphedMatchStick matchStickToMorph, HashSet<Integer> componentsToRemove) {
        MorphedMatchStick removedLimbMatchStick = new MorphedMatchStick();
        removedLimbMatchStick.setProperties(getScaleForMAxisShape(), matchStickToMorph.getTextureType(), 1.0);
        removedLimbMatchStick.genRemovedLimbsMatchStick(matchStickToMorph, componentsToRemove);
        return removedLimbMatchStick;
    }

    private HashSet<Integer> specifyCompsToRemove(MorphedMatchStick matchStickToMorph, double magnitude) {
        int currentNComp = matchStickToMorph.getNComponent();
        HashSet<Integer> componentsToRemove = new HashSet<>();

        // Find max and min number of components allowed
        int maxNComp = findMaxIndex(PARAM_nCompDist) + 1;
        int minNComp = findMinIndex(PARAM_nCompDist) + 1;

        // Ensure the min and max are within valid range
        if (minNComp < 1) minNComp = 1;
        if (maxNComp > currentNComp) maxNComp = currentNComp;

        // Calculate the number of components to remove based on a simple strategy
        int componentsToRemoveCount = calculateNCompsToRemove(currentNComp, minNComp, maxNComp, magnitude);
        System.out.println("Removing " + componentsToRemoveCount + " components");
        // Randomly choose components to remove

        while (componentsToRemove.size() < componentsToRemoveCount) {
            int componentId = (int) (Math.random() * currentNComp) + 1; // Assuming component IDs start at 1
            if (matchStickToMorph.getLeafBranch()[componentId]) continue; // Skip if it is a branch
            componentsToRemove.add(componentId);
        }
        return componentsToRemove;
    }

    public static int findMaxIndex(double[] array) {
        for (int i = array.length - 1; i >= 0; i--) {
            if (array[i] != 0.0) return i;
        }
        return -1; // Default case, though this should not happen with valid data
    }

    public static int findMinIndex(double[] array) {
        for (int i = 0; i < array.length; i++) {
            if (array[i] != 0.0) return i;
        }
        return -1; // Default case, though this should not happen with valid data
    }

    public static int calculateNCompsToRemove(int currentNComp, int minNComp, int maxNComp, double magnitude) {
        if (minNComp == maxNComp) return 0; // No removal if min and max are the same
        if (currentNComp <= minNComp) return 0; // No removal if current is at or below min
        if (Math.random()< magnitude)
            return 1;
        else
            return 0;
//        int range = maxNComp - minNComp;
//        return (int) (Math.random() * (range + 1)) + (currentNComp - maxNComp);
    }


    private Map<Integer, ComponentMorphParameters> specifyOutsideRFCompMorphParams(MorphedMatchStick matchStickToMorph, double magnitude) {
        NormalMorphDistributer normalMorphDistributer = new NormalMorphDistributer(sigma);
        // Construct MorphParameters for components
        Map<Integer, ComponentMorphParameters> paramsForComps = new HashMap<Integer, ComponentMorphParameters>();
        for (int i = 1; i<= matchStickToMorph.getNComponent(); i++) {
            if (i!=matchStickToMorph.getSpecialEndComp().get(0)) {
                ComponentMorphParameters params = new NormalDistributedComponentMorphParameters(magnitude, normalMorphDistributer);
                paramsForComps.put(i, params);
            }
        }
        return paramsForComps;
    }


    private Map<Integer, ComponentMorphParameters> specifyInsideRFCompMorphParams(MorphedMatchStick matchStickToMorph, double magnitude) {
        NormalMorphDistributer normalMorphDistributer = new NormalMorphDistributer(sigma);
        // Construct MorphParameters for components
        Map<Integer, ComponentMorphParameters> paramsForComps = new HashMap<Integer, ComponentMorphParameters>();

        ComponentMorphParameters params = new NormalDistributedComponentMorphParameters(magnitude, normalMorphDistributer);
        paramsForComps.put(matchStickToMorph.getSpecialEndComp().get(0), params);


        return paramsForComps;
    }

    public static Map<Integer, ComponentMorphParameters> specifyCompMorphParams(MorphedMatchStick matchStickToMorph, double magnitude, double sigma1) {
        NormalMorphDistributer normalMorphDistributer = new NormalMorphDistributer(sigma1);
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