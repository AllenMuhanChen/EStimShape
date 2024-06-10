package org.xper.allen.drawing.composition.morph;

import com.thoughtworks.xstream.XStream;
import org.xper.allen.drawing.composition.*;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.pga.RFStrategy;

import java.util.*;

public class PruningMatchStick extends GAMatchStick {

    private MorphedMatchStick matchStickToMorph;
    private List<Integer> toPreserve;
    private List<Integer> componentsToMorph;

    public PruningMatchStick(ReceptiveField rf, RFStrategy rfStrategy) {
        super(rf, rfStrategy, "SHADE");
    }

    public PruningMatchStick() {
        super();
    }

    // Chooses own random components to preserve
    public void genPruningMatchStick(MorphedMatchStick matchStickToMorph, double magnitude, int numPreserve){
        this.matchStickToMorph = matchStickToMorph;

        componentsToMorph = chooseComponentsToMorph(numPreserve);

        NormalMorphDistributer normalMorphDistributer = new NormalMorphDistributer(1/3.0);
        // Construct MorphParameters for componentsToMorph
        Map<Integer, ComponentMorphParameters> paramsForComps = new HashMap<>();
        for (Integer comp : componentsToMorph) {
            ComponentMorphParameters params = new NormalDistributedComponentMorphParameters(magnitude, normalMorphDistributer);
            paramsForComps.put(comp, params);
        }

        // Call MorphedMatchStick
        genMorphedComponentsMatchStick(paramsForComps, this.matchStickToMorph, true);

    }

    private List<Integer> chooseComponentsToMorph(int numPreserve) {
        List<Integer> componentsToMorph = matchStickToMorph.getCompIds();
        Collections.shuffle(componentsToMorph);
        toPreserve = new ArrayList<Integer>();
        for (int i = 0; i< numPreserve; i++){
            toPreserve.add(componentsToMorph.get(i));
        }
        componentsToMorph.removeAll(toPreserve);
        return componentsToMorph;
    }

    @Override
    public PruningMStickData getMStickData(){
        AllenMStickData superData = super.getMStickData();

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