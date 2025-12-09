package org.xper.allen.drawing.composition.morph;

import com.thoughtworks.xstream.XStream;
import org.xper.allen.drawing.composition.*;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.noisy.NAFCNoiseMapper;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;
import org.xper.drawing.stick.JuncPt_struct;

import javax.vecmath.Point3d;
import java.util.*;

public class PruningMatchStick extends ProceduralMatchStick {

    private MorphedMatchStick matchStickToMorph;
    private List<Integer> toPreserveInParent = new ArrayList<>();
    private List<Integer> preservedComps = new ArrayList<>();

    public PruningMatchStick(ReceptiveField rf, RFStrategy rfStrategy, NAFCNoiseMapper noiseMapper) {
        super(rf, rfStrategy, noiseMapper);
    }

    /**
     * Behavior of this one is to automatically position shape based on parent shape
     * @param noiseMapper
     */
    public PruningMatchStick(NAFCNoiseMapper noiseMapper) {
        super(noiseMapper);
    }

    public void genMatchStickFromComponentsInNoise(AllenMatchStick baseMatchStick, List<Integer> fromComponents, int nComp, boolean doCompareObjCenteredPos, int maxAttempts1){
        this.toPreserveInParent = new ArrayList<>();
        this.toPreserveInParent.addAll(fromComponents);
        preservedComps.add(1);
        preservedComps.add(2);
        this.matchStickToMorph = (MorphedMatchStick) baseMatchStick;
        super.genMatchStickFromComponentInNoise(baseMatchStick, fromComponents, nComp, doCompareObjCenteredPos, maxAttempts1);
    }

    /**
     *
     * @param matchStickToMorph
     * @param magnitude
     * @param compsToPreserve
     * @param compsToNoise: null - then will default to compsToPreserve
     */
    public void genPruningMatchStick(MorphedMatchStick matchStickToMorph, double magnitude, List<Integer> compsToPreserve, List<Integer> compsToNoise){
        this.matchStickToMorph = matchStickToMorph;
        this.toPreserveInParent = compsToPreserve;
        preservedComps.addAll(compsToPreserve);
        List<Integer> componentsToMorph = chooseComponentsToMorph(compsToPreserve);
        if (compsToNoise == null){
            setSpecialEndComp(componentsToMorph);
            this.matchStickToMorph.setSpecialEndComp(componentsToMorph); //setting this as well otherwise this will be overriden during generation
        } else{
            setSpecialEndComp(compsToNoise);
            this.matchStickToMorph.setSpecialEndComp(compsToNoise);
        }


        // MORPH ALL COMPONENTS STRATEGY
        NormalMorphDistributer normalMorphDistributer = new NormalMorphDistributer(1/3.0);
        // Construct MorphParameters for componentsToMorph
        Map<Integer, ComponentMorphParameters> paramsForComps = new HashMap<>();
        for (Integer comp : componentsToMorph) {
            ComponentMorphParameters params = new NormalDistributedComponentMorphParameters(magnitude, normalMorphDistributer);
            paramsForComps.put(comp, params);
        }

        // Call MorphedMatchStick
        int nAttempts = 0;
        while (nAttempts < getMaxTotalAttempts()) {
            try {
                nAttempts++;
                boolean doPositionShape = true;
                boolean doPreserveJunction = true;
                boolean doCheckObjCentPosition = true;
                genMorphedComponentsMatchStick(paramsForComps, this.matchStickToMorph,
                        doPositionShape,
                        doPreserveJunction,
                        doCheckObjCentPosition);
                noiseMapper.checkInNoise(this, compsToPreserve, 0.5);
                System.out.println("success!");
                return;
            } catch(Exception e) {
                System.out.println(e.getMessage());

            }
        }
        throw new MorphRepetitionException("Exceeded max number of attempts when generating pruning mstick");
    }

    public List<Integer> getPreservedComps() {
        return preservedComps;
    }

    @Override
    protected void positionShape() throws MorphException {
        if (rfStrategy != null) {
            RFUtils.positionAroundRF(rfStrategy, this, rf, 1000);
        } else{
            Point3d pointToMove = getComp()[preservedComps.get(0)].getMassCenter();
            Point3d destination = matchStickToMorph.getComp()[toPreserveInParent.get(0)].getMassCenter();

            movePointToDestination(pointToMove, destination);
        }
    }

    public static List<Integer> chooseRandomComponentsToPreserve(MorphedMatchStick stickToMorph) {
        List<List<Integer>> allValidCombinations = new ArrayList<>();

        // Add all single component combinations (excluding invalid index 0)
        for (int compId : stickToMorph.getCompIds()) {
            if (compId != 0) {  // exclude invalid index
                allValidCombinations.add(Collections.singletonList(compId));
            }
        }

        // Add all valid pairs (components that share a junction, excluding invalid index 0)
        for (JuncPt_struct junc : stickToMorph.getJuncPt()) {
            if (junc == null) continue;

            // Collect non-zero components in this junction
            List<Integer> compsInJunc = new ArrayList<>();
            for (int compId : junc.getCompIds()) {
                if (compId != 0) {  // exclude invalid index
                    compsInJunc.add(compId);
                }
            }

            // Generate all pairs from this junction
            for (int i = 0; i < compsInJunc.size(); i++) {
                for (int j = i + 1; j < compsInJunc.size(); j++) {
                    allValidCombinations.add(Arrays.asList(compsInJunc.get(i), compsInJunc.get(j)));
                }
            }
        }

        // Randomly select one combination with equal probability
        Collections.shuffle(allValidCombinations);
        return allValidCombinations.get(0);
    }

    // Chooses own random components to preserve
    public static List<Integer> chooseRandomComponentsToPreserve(int numPreserve, MorphedMatchStick stickToMorph) {
//        if (stickToMorph.getNComponent() <= numPreserve){
//            throw new RuntimeException("Preserving more components than mstick contains");
//        }
        List<Integer> componentsToPreserve = new ArrayList<>();

        if (numPreserve == 1){
            List<Integer> components = new ArrayList<>(stickToMorph.getCompIds());
            Collections.shuffle(components);
            for  (int i = 0; i < numPreserve; i++) {
                componentsToPreserve.add(components.get(i));
            }
        } else if (numPreserve == 2){
            int randomLeaf = stickToMorph.chooseRandLeaf();
            componentsToPreserve.add(randomLeaf);

            List<Integer> choosableBranches = new ArrayList<>();
            JuncPt_struct juncThatContainsRandomLeaf = null;
            for (JuncPt_struct junc : stickToMorph.getJuncPt()) {
                if (junc == null) continue;
                // look for junc that contains random leaf
                for (int compId : junc.getCompIds()) {
                    if (compId == randomLeaf) {
                        juncThatContainsRandomLeaf = junc;
                        break;
                    }
                }
            }
            // go through comps in junction and add compatible
            for (int compId : juncThatContainsRandomLeaf.getCompIds()) {
                if (compId != randomLeaf && compId != 0){
                    choosableBranches.add(compId);
                }
            }


            Collections.shuffle(choosableBranches);
            componentsToPreserve.add(choosableBranches.get(0));
            System.out.println("COMPONENTS TO PRESERVE: " + componentsToPreserve.toString());
        }
        return componentsToPreserve;
    }

    private List<Integer> chooseComponentsToMorph(List<Integer> compsToPreserve){
        List<Integer> componentsToMorph = new ArrayList<>();
        for (Integer comp : matchStickToMorph.getCompIds()) {
            if (!compsToPreserve.contains(comp)) {
                componentsToMorph.add(comp);
            }
        }
        return  componentsToMorph;
    }

    @Override
    public PruningMStickData getMStickData(){
        AllenMStickData superData = (AllenMStickData) super.getMStickData();

        return new PruningMStickData(superData, toPreserveInParent);

    }

    public static class PruningMStickData extends AllenMStickData {
        List<Integer> componentsToPreserve;

        public PruningMStickData(AllenMStickData superData, List<Integer> componentsToPreserve) {
            super(superData);
            this.componentsToPreserve = componentsToPreserve;
        }

        public PruningMStickData() {
        }

        static XStream s;

        static {
            s = new XStream();
            s.alias("AllenMStickData", PruningMStickData.class);
            s.alias("TerminationData", TerminationData.class);
            s.alias("JunctionData", JunctionData.class);
            s.alias("ShaftData", ShaftData.class);
            s.alias("AllenMSickSpec", AllenMStickSpec.class);
        }

        public String toXml() {
            return PruningMStickData.toXml(this);
        }

        public static String toXml(PruningMStickData data){
            return s.toXML(data);
        }

        public static PruningMStickData fromXml(String xml){
            return (PruningMStickData) s.fromXML(xml);
        }

        public List<Integer> getComponentsToPreserve() {
            return componentsToPreserve;
        }

        public void setComponentsToPreserve(List<Integer> componentsToPreserve) {
            this.componentsToPreserve = componentsToPreserve;
        }
    }

    public List<Integer> getComponentsToPreserve() {
        return toPreserveInParent;
    }
}