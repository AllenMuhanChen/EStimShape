package org.xper.allen.drawing.composition.morph;

import com.thoughtworks.xstream.XStream;
import org.xper.allen.drawing.composition.*;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;
import org.xper.allen.util.CoordinateConverter;

import javax.vecmath.Point3d;
import java.util.*;

import static org.xper.allen.drawing.composition.experiment.ProceduralMatchStick.compareObjectCenteredPositions;

public class PruningMatchStick extends GAMatchStick {

    private MorphedMatchStick matchStickToMorph;
    private List<Integer> toPreserve;
    private List<Integer> componentsToMorph;

    public PruningMatchStick(ReceptiveField rf, RFStrategy rfStrategy) {
        super(rf, rfStrategy);
    }

    public PruningMatchStick() {
    }

    public void genPruningMatchStick(MorphedMatchStick matchStickToMorph, double magnitude, int numPreserve){
        this.matchStickToMorph = matchStickToMorph;


        componentsToMorph = chooseComponentsToMorph(numPreserve);

        // MORPH ALL COMPONENTS STRATEGY
        NormalMorphDistributer normalMorphDistributer = new NormalMorphDistributer(1/3.0);
        // Construct MorphParameters for componentsToMorph
        Map<Integer, ComponentMorphParameters> paramsForComps = new HashMap<>();
        for (Integer comp : componentsToMorph) {
            ComponentMorphParameters params = new NormalDistributedComponentMorphParameters(magnitude, normalMorphDistributer);
            paramsForComps.put(comp, params);
        }

        // Call MorphedMatchStick
        genMorphedComponentsMatchStick(paramsForComps, this.matchStickToMorph, true, true, true);
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