package org.xper.allen.nafc.blockgen.estimshape;

import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.nafc.blockgen.procedural.ProceduralStim;

import java.util.Map;

public class EStimShapePsychometricTwoByTwoParameters extends ProceduralStim.ProceduralStimParameters{

    private final AllenMStickSpec sampleSpec;
    private final Map<String, AllenMStickSpec> baseProceduralDistractorSpecs;
    private final boolean isEStimEnabled;
    private final String sampleSetCondition;
    private final double baseMagnitude;
    private final double drivingMagnitude;
    private final boolean isDeltaNoise;

    public EStimShapePsychometricTwoByTwoParameters(ProceduralStim.ProceduralStimParameters parameters, AllenMStickSpec sampleSpec, Map<String, AllenMStickSpec> baseProceduralDistractorSpecs, boolean isEStimEnabled, String sampleSetCondition, double baseMagnitude, double drivingMagnitude, boolean isDeltaNoise) {
        super(parameters);
        this.sampleSpec = sampleSpec;
        this.baseProceduralDistractorSpecs = baseProceduralDistractorSpecs;
        this.isEStimEnabled = isEStimEnabled;
        this.sampleSetCondition = sampleSetCondition;
        this.baseMagnitude = baseMagnitude;
        this.drivingMagnitude = drivingMagnitude;
        this.isDeltaNoise = isDeltaNoise;
    }

    public EStimShapePsychometricTwoByTwoParameters(EStimShapePsychometricTwoByTwoParameters other) {
        super(other);
        this.sampleSpec = other.sampleSpec;
        this.baseProceduralDistractorSpecs = other.baseProceduralDistractorSpecs;
        this.isEStimEnabled = other.isEStimEnabled;
        this.sampleSetCondition = other.sampleSetCondition;
        this.baseMagnitude = other.baseMagnitude;
        this.drivingMagnitude = other.drivingMagnitude;
        this.isDeltaNoise = other.isDeltaNoise;
    }

    public AllenMStickSpec getSampleSpec() {
        return sampleSpec;
    }

    public Map<String, AllenMStickSpec> getBaseProceduralDistractorSpecs() {
        return baseProceduralDistractorSpecs;
    }

    public boolean isEStimEnabled() {
        return isEStimEnabled;
    }

    public String getSampleSetCondition() {
        return sampleSetCondition;
    }

    public double getBaseMagnitude() {
        return baseMagnitude;
    }

    public double getDrivingMagnitude() {
        return drivingMagnitude;
    }

    public boolean isDeltaNoise() {
        return isDeltaNoise;
    }
}