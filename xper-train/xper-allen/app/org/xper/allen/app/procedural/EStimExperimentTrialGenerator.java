package org.xper.allen.app.procedural;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.Dependency;
import org.xper.allen.Stim;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.blockgen.procedural.*;
import org.xper.allen.nafc.blockgen.procedural.ProceduralStim.ProceduralStimParameters;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;
import org.xper.allen.pga.ReceptiveFieldSource;
import org.xper.exception.XGLException;
import org.xper.util.FileUtil;

import javax.swing.*;
import java.awt.*;
import java.util.LinkedHashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
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
        //input Parameters
        Color stimColor = new Color(0.5f, 0.5f, 0.5f);
        long stimId = 1716913436993343L;
        int compId = 2;

        //Parameters
        Map<Double, Integer> numEStimTrialsForNoiseChances = new LinkedHashMap<>();
        numEStimTrialsForNoiseChances.put(0.5, 10);

        int numDeltaSets = 0;

        Map<Double, Integer> numBehavioralTrialsForNoiseChances = new LinkedHashMap<>();
//        numBehavioralTrialsForNoiseChances.put(0.5, 10);

        List<ProceduralStimParameters> eStimTrialParams = assignTrialParams(stimColor, numEStimTrialsForNoiseChances);
        List<ProceduralStimParameters> behavioralTrialParams = assignTrialParams(stimColor, numBehavioralTrialsForNoiseChances);

        //Make Trials
        List<Stim> eStimTrials = makeEStimTrials(eStimTrialParams, stimColor, stimId, compId);
        List<Stim> deltaTrials = makeDeltaTrials(numDeltaSets, eStimTrialParams, eStimTrials);
        List<Stim> behavioralTrials = makeBehavioralTrials(behavioralTrialParams);
        stims.addAll(eStimTrials);
        stims.addAll(deltaTrials);
        stims.addAll(behavioralTrials);
    }

    private List<Stim> makeEStimTrials(List<ProceduralStimParameters> eStimTrialParams, Color stimColor, long stimId, int compId) {
        List<Stim> eStimTrials = new LinkedList<>();
        //Add EStim Trials
        for (ProceduralStimParameters parameters : eStimTrialParams) {
            ProceduralMatchStick baseMStick = new ProceduralMatchStick();
            baseMStick.setProperties(RFUtils.calculateMStickMaxSizeDegrees(RFStrategy.PARTIALLY_INSIDE, rfSource), "SHADE");
            baseMStick.setStimColor(stimColor);
            baseMStick.genMatchStickFromFile(gaSpecPath + "/" + stimId + "_spec.xml");
            //using estim values set on the IntanGUI
            EStimProceduralStim stim = new EStimProceduralStim(
                    this,
                    parameters, baseMStick, compId, compId);
            eStimTrials.add(stim);
        }
        return eStimTrials;
    }

    private static List<Stim> makeDeltaTrials(int numDeltaSets, List<ProceduralStimParameters> eStimTrialParams, List<Stim> eStimTrials) {
        //Add Delta Trials
        List<Stim> deltaTrials = new LinkedList<>();
        for (int i = 0; i< numDeltaSets; i++){
            int randIndex = (int) (Math.random() * eStimTrialParams.size());
            ProceduralStim baseStim = (ProceduralStim) eStimTrials.get(randIndex);
            ProceduralStim deltaMorph = new DeltaStim(baseStim, true, false);
            ProceduralStim deltaNoise = new DeltaStim(baseStim, false, true);
            ProceduralStim deltaBoth = new DeltaStim(baseStim, true, true);
            deltaTrials.add(deltaMorph);
            deltaTrials.add(deltaNoise);
            deltaTrials.add(deltaBoth);
        }
        return deltaTrials;
    }

    private List<Stim> makeBehavioralTrials(List<ProceduralStimParameters> behavioralTrialParams) {
        //Add Behavioral Trials
        List<Stim> behavioralTrials = new LinkedList<>();
        for (ProceduralStimParameters parameters : behavioralTrialParams){
            ProceduralStim stim = new ProceduralRandStim(this, parameters);
            behavioralTrials.add(stim);
        }
        return behavioralTrials;
    }

    private List<ProceduralStimParameters> assignTrialParams(Color stimColor, Map<Double, Integer> numTrialsForNoiseChances) {
        //Init EStim Trial Parameters
        List<ProceduralStimParameters> eStimTrialParams = new LinkedList<>();
        numTrialsForNoiseChances.forEach(new BiConsumer<Double, Integer>() {
            @Override
            public void accept(Double noiseChance, Integer numTrials) {
                for (int i = 0; i < numTrials; i++) {
                    ProceduralStimParameters parameters = new ProceduralStimParameters(
                            new Lims(0, 0),
                            new Lims(10, 10),
                            getImageDimensionsDegrees(), //not used?
                            RFUtils.calculateMStickMaxSizeDegrees(RFStrategy.PARTIALLY_INSIDE, rfSource),
                            noiseChance,
                            4,
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