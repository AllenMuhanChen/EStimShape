package org.xper.allen.app.procedural;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.Dependency;
import org.xper.allen.Stim;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.ga.CircleReceptiveField;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.blockgen.procedural.*;
import org.xper.allen.nafc.blockgen.procedural.ProceduralStim.ProceduralStimParameters;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;
import org.xper.allen.pga.ReceptiveFieldSource;
import org.xper.drawing.Coordinates2D;
import org.xper.exception.XGLException;
import org.xper.util.FileUtil;

import javax.swing.*;
import java.awt.*;
import java.util.*;
import java.util.List;
import java.util.function.BiConsumer;

public class EStimExperimentTrialGenerator extends NAFCBlockGen {
    @Dependency
    String gaSpecPath;

    @Dependency
    ReceptiveFieldSource rfSource;

    public static void main(String[] args) {
        try {
            UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
        } catch (Exception e) {
            throw new XGLException(e);
        }

        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"));
        EStimExperimentTrialGenerator generator = context.getBean(EStimExperimentTrialGenerator.class);
        generator.generate();
    }

    @Override
    protected void addTrials() {
//        addTrials_Deltas();
        addTrials_TwoByTwo();
    }

    private void addTrials_TwoByTwo(){
        //input Parameters
        Color stimColor = new Color(0.5f, 0.5f, 0.5f);
        long stimId = 1717531847396095L;
        int compId = 2;

        //Parameters
        Map<Double, Integer> numEStimTrialsForNoiseChances = new LinkedHashMap<>();
        numEStimTrialsForNoiseChances.put(0.5, 10);

        Map<Double, Integer> numBehavioralTrialsForNoiseChances = new LinkedHashMap<>();
        numBehavioralTrialsForNoiseChances.put(0.5, 30);

        List<ProceduralStimParameters> eStimTrialParams = assignTrialParams(stimColor, numEStimTrialsForNoiseChances);
        List<ProceduralStimParameters> behavioralTrialParams = assignTrialParams(stimColor, numBehavioralTrialsForNoiseChances);

        List<Stim> eStimTrials = new LinkedList<>();
        //Add EStim Trials
        for (ProceduralStimParameters parameters : eStimTrialParams) {
            ProceduralMatchStick baseMStick = new ProceduralMatchStick();
            baseMStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, rfSource), "SHADE");
            baseMStick.setStimColor(stimColor);
            baseMStick.genMatchStickFromFile(gaSpecPath + "/" + stimId + "_spec.xml");
            //using estim values set on the IntanGUI
            EStimShapeTwoByTwoStim eStimTrial = new EStimShapeTwoByTwoStim(
                    this,
                    parameters, baseMStick, compId, true);
            EStimShapeTwoByTwoStim negativeControlTrial = new EStimShapeTwoByTwoStim(
                    this,
                    parameters, baseMStick, compId, false);
            eStimTrials.add(eStimTrial);
            eStimTrials.add(negativeControlTrial);
        }

        //Add Behavioral Trials
        List<ReceptiveField> behTrialRFs = assignRFsToBehTrials(eStimTrials.size(), 0, behavioralTrialParams.size(), getRF());

        List<Stim> behavioralTrials = new LinkedList<>();
        for (int i = 0; i< behavioralTrialParams.size(); i++){
            ProceduralStimParameters parameters = behavioralTrialParams.get(i);
            EStimShapeTwoByTwoBehavioralStim stim = new EStimShapeTwoByTwoBehavioralStim(this, parameters, behTrialRFs.get(i));
            behavioralTrials.add(stim);
        }


//        stims.addAll(behavioralTrials);
        stims.addAll(eStimTrials);

    }

    private void addTrials_Deltas() {
        //input Parameters
        Color stimColor = new Color(0.5f, 0.5f, 0.5f);
        long stimId = 1717531847396095L;
        int compId = 2;

        //Parameters
        Map<Double, Integer> numEStimTrialsForNoiseChances = new LinkedHashMap<>();
        numEStimTrialsForNoiseChances.put(0.5, 5);

        int numDeltaSets = 0;

        Map<Double, Integer> numBehavioralTrialsForNoiseChances = new LinkedHashMap<>();
        numBehavioralTrialsForNoiseChances.put(0.5, 20);

        List<ProceduralStimParameters> eStimTrialParams = assignTrialParams(stimColor, numEStimTrialsForNoiseChances);
        List<ProceduralStimParameters> behavioralTrialParams = assignTrialParams(stimColor, numBehavioralTrialsForNoiseChances);

        //Make EStimTrials and Delta Trials
        List<Stim> eStimTrials = makeEStimTrials(eStimTrialParams, stimColor, stimId, compId);
        List<Stim> deltaTrials = makeDeltaTrials(numDeltaSets, eStimTrialParams, eStimTrials);

        //Assigning Fake RFS
        int numEStimTrials = eStimTrials.size();
        int numDeltaTrials = deltaTrials.size();
        int numBehavioralTrials = behavioralTrialParams.size();
        List<ReceptiveField> behTrialRFs = assignRFsToBehTrials(numEStimTrials, numDeltaTrials, numBehavioralTrials, getRF());

        List<Stim> behavioralTrials = makeBehavioralTrials(behavioralTrialParams, behTrialRFs);
        stims.addAll(behavioralTrials);
        stims.addAll(eStimTrials);
        stims.addAll(deltaTrials);

    }

    public static List<ReceptiveField> assignRFsToBehTrials(int numEStimTrials, int numDeltaTrials, int numBehavioralTrials, ReceptiveField realRf) {
        int numTestTrials = numEStimTrials + numDeltaTrials;
        int numTotalTrials = numTestTrials + numBehavioralTrials;
        int numToDistributeToFakeRFs = numTotalTrials - (2*numTestTrials);
        double numRFs = (double) numTotalTrials / numToDistributeToFakeRFs;
        if (numRFs % 1 != 0){
            throw new IllegalArgumentException("Number of Behavioral Trials must be a multiple of the number of EStimTrials and DeltaTrials");
        }
        int numFakeRFs = (int) (numRFs - 1); //minus one for the real one
        int numTrialsPerRF = (int) (numTotalTrials/numRFs);
        double eccentricity = realRf.getCenter().distance(new Coordinates2D(0, 0));
        double angleDf = 360.0 / numRFs;

        double realRFAngle = RFUtils.cartesianToPolarAngle(realRf.getCenter());
        Set<ReceptiveField> fakeRFs = new HashSet<>();
        for (int i = 1; i <= numFakeRFs; i++){
            double angle = realRFAngle + angleDf * i;
            Coordinates2D fakeCenter = RFUtils.polarToCartesian(eccentricity, angle);
            ReceptiveField fakeRF = new CircleReceptiveField(fakeCenter, realRf.radius);
            fakeRFs.add(fakeRF);
        }

        List<ReceptiveField> behTrialRFs = new LinkedList<>();
        //Assign To Fake RFs
        fakeRFs.forEach(new java.util.function.Consumer<ReceptiveField>() {
            @Override
            public void accept(ReceptiveField fakeRF) {
                for (int i = 0; i < numTrialsPerRF; i++){
                    behTrialRFs.add(fakeRF);
                }
            }
        }
        );
        //Assign to Real RF
        for (int i=0; i<numTrialsPerRF/2; i++){
            behTrialRFs.add(realRf);
        }
        return behTrialRFs;
    }

    private List<Stim> makeEStimTrials(List<ProceduralStimParameters> eStimTrialParams, Color stimColor, long stimId, int compId) {
        List<Stim> eStimTrials = new LinkedList<>();
        //Add EStim Trials
        for (ProceduralStimParameters parameters : eStimTrialParams) {
            ProceduralMatchStick baseMStick = new ProceduralMatchStick();
            baseMStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, rfSource), "SHADE");
            baseMStick.setStimColor(stimColor);
            baseMStick.genMatchStickFromFile(gaSpecPath + "/" + stimId + "_spec.xml");
            //using estim values set on the IntanGUI
            EStimShapeProceduralStim eStimTrial = new EStimShapeProceduralStim(
                    this,
                    parameters, baseMStick, compId, true);
            EStimShapeProceduralStim negativeControlTrial = new EStimShapeProceduralStim(
                    this,
                    parameters, baseMStick, compId, false);
            eStimTrials.add(eStimTrial);
            eStimTrials.add(negativeControlTrial);
        }
        return eStimTrials;
    }

    private static List<Stim> makeDeltaTrials(int numDeltaSets, List<ProceduralStimParameters> eStimTrialParams, List<Stim> eStimTrials) {
        //Add Delta Trials
        List<Stim> deltaTrials = new LinkedList<>();
        for (int i = 0; i< numDeltaSets; i++){
            int randIndex = (int) (Math.random() * eStimTrialParams.size());
            EStimShapeProceduralStim baseStim = (EStimShapeProceduralStim) eStimTrials.get(randIndex);
            EStimShapeDeltaStim deltaMorph = new EStimShapeDeltaStim(baseStim, true, false);
            EStimShapeDeltaStim deltaNoise = new EStimShapeDeltaStim(baseStim, false, true);
            EStimShapeDeltaStim deltaBoth = new EStimShapeDeltaStim(baseStim, true, true);
            deltaTrials.add(deltaMorph);
            deltaTrials.add(deltaNoise);
            deltaTrials.add(deltaBoth);
        }
        return deltaTrials;
    }

    private List<Stim> makeBehavioralTrials(List<ProceduralStimParameters> behavioralTrialParams, List<ReceptiveField> fakeRFs) {
        //Add Behavioral Trials
        List<Stim> behavioralTrials = new LinkedList<>();
        for (int i = 0; i< behavioralTrialParams.size(); i++){
            ProceduralStimParameters parameters = behavioralTrialParams.get(i);
            EStimShapeProceduralBehavioralStim stim = new EStimShapeProceduralBehavioralStim(this, parameters, fakeRFs.get(i));
            behavioralTrials.add(stim);
        }

        return behavioralTrials;
    }

    private List<ProceduralStimParameters> assignTrialParams(Color stimColor, Map<Double, Integer> numTrialsForNoiseChances) {
        //Specifying universal parameters
        double eyeWinRadius = calculateEyeWinRadius();
        int numChoices = 4;
        double choiceRadius = RadialSquares.calculateRequiredRadius(
                numChoices,
                eyeWinRadius,
                eyeWinRadius/2);

        //Init EStim Trial Parameters
        List<ProceduralStimParameters> eStimTrialParams = new LinkedList<>();
        numTrialsForNoiseChances.forEach(new BiConsumer<Double, Integer>() {
            @Override
            public void accept(Double noiseChance, Integer numTrials) {

                for (int i = 0; i < numTrials; i++) {

                    ProceduralStimParameters parameters = new ProceduralStimParameters(
                            new Lims(0, 0),
                            new Lims(choiceRadius, choiceRadius),
                            getImageDimensionsDegrees(), //not used?
                            eyeWinRadius,
                            noiseChance,
                            numChoices,
                            2,
                            0.5,
                            0.5,
                            stimColor,
                            "SHADE"
                    );

                    eStimTrialParams.add(parameters);
                }
            }
        });
        return eStimTrialParams;
    }

    private double calculateEyeWinRadius() {
        double shapeSquareLength = RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, rfSource);
        double squareDiagonal = Math.sqrt(2) * shapeSquareLength;
        double eyeWinRadius = squareDiagonal /2;
        return eyeWinRadius;
    }

    public ReceptiveField getRF() {
        return rfSource.getReceptiveField();
    }

    public String getGaSpecPath() {
        return gaSpecPath;
    }

    public void setGaSpecPath(String gaSpecPath) {
        this.gaSpecPath = gaSpecPath;
    }

    public ReceptiveFieldSource getRfSource() {
        return rfSource;
    }

    public void setRfSource(ReceptiveFieldSource rfSource) {
        this.rfSource = rfSource;
    }
}