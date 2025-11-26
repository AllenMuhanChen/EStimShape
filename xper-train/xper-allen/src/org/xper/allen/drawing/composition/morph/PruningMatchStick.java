package org.xper.allen.drawing.composition.morph;

import com.thoughtworks.xstream.XStream;
import org.xper.allen.drawing.composition.*;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.noisy.NAFCNoiseMapper;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;

import javax.vecmath.Point3d;
import java.util.*;

public class PruningMatchStick extends ProceduralMatchStick {

    private MorphedMatchStick matchStickToMorph;
    private List<Integer> toPreserve = new ArrayList<>();
    private List<Integer> componentsToMorph;

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

    public void genPruningMatchStick(MorphedMatchStick matchStickToMorph, double magnitude, List<Integer> compsToPreserve, List<Integer> compsToNoise){
        this.matchStickToMorph = matchStickToMorph;
        this.toPreserve = compsToPreserve;
        componentsToMorph = chooseComponentsToMorph(compsToPreserve);
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
        while (nAttempts < 15) {
            try {
                nAttempts++;
                genMorphedComponentsMatchStick(paramsForComps, this.matchStickToMorph, true, true, true);
                noiseMapper.checkInNoise(this, compsToPreserve, 0.5);
                return;
            } catch(Exception e) {
                System.out.println(e.getMessage());

            }
        }

        // BASE MATCH STICK STRATEGY?
    }

    @Override
    protected void positionShape() throws MorphException {
        if (rfStrategy != null) {
            RFUtils.positionAroundRF(rfStrategy, this, rf, 1000);
        } else{
            int compToMove = toPreserve.get(0);
            Point3d pointToMove = getComp()[compToMove].getMassCenter();
            Point3d destination = matchStickToMorph.getComp()[compToMove].getMassCenter();

            movePointToDestination(pointToMove, destination);
        }
    }

    // Chooses own random components to preserve

    public static List<Integer> chooseRandomComponentsToPreserve(int numPreserve, MorphedMatchStick stickToMorph) {
        List<Integer> componentsToPreserve = new ArrayList<>();
        List<Integer> components = stickToMorph.getCompIds();
        Collections.shuffle(components);
        for  (int i = 0; i < numPreserve; i++) {
            componentsToPreserve.add(components.get(i));
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