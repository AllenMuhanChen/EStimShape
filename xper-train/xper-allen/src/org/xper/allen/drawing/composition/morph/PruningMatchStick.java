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
    private List<Integer> toPreserve = new ArrayList<>();
    private Integer preservedComp;
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

    public void genMatchStickFromComponentInNoise(AllenMatchStick baseMatchStick, int fromCompId, int nComp, boolean doCompareObjCenteredPos, int maxAttempts1){
        this.toPreserve = new ArrayList<>();
        this.toPreserve.add(fromCompId);
        preservedComp = 1; //r

        this.matchStickToMorph = (MorphedMatchStick) baseMatchStick;
        super.genMatchStickFromComponentInNoise(baseMatchStick, fromCompId, nComp, doCompareObjCenteredPos, maxAttempts1);
    }

    public void genPruningMatchStick(MorphedMatchStick matchStickToMorph, double magnitude, List<Integer> compsToPreserve, List<Integer> compsToNoise){
        this.matchStickToMorph = matchStickToMorph;
        this.toPreserve = compsToPreserve;
        preservedComp = toPreserve.get(0); //r
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
                genMorphedComponentsMatchStick(paramsForComps, this.matchStickToMorph, true, true, false);
//                noiseMapper.checkInNoise(this, compsToPreserve, 0.5);
                System.out.println("success!");
                return;
            } catch(Exception e) {
                System.out.println(e.getMessage());

            }
        }
        throw new MorphRepetitionException("Exceeded max number of attempts when generating pruning mstick");

        // BASE MATCH STICK STRATEGY?
    }


    @Override
    protected void positionShape() throws MorphException {
        if (rfStrategy != null) {
            RFUtils.positionAroundRF(rfStrategy, this, rf, 1000);
        } else{
            Point3d pointToMove = getComp()[preservedComps.get(0)].getMassCenter();
            Point3d destination = matchStickToMorph.getComp()[toPreserve.get(0)].getMassCenter();

            movePointToDestination(pointToMove, destination);
        }
    }

    // Chooses own random components to preserve

    public static List<Integer> chooseRandomComponentsToPreserve(int numPreserve, MorphedMatchStick stickToMorph) {
        if (stickToMorph.getNComponent() <= numPreserve){
            throw new RuntimeException("Preserving more components than mstick contains");
        }
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

        return new PruningMStickData(superData, toPreserve);

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
        return toPreserve;
    }
}