package org.xper.allen.isoluminant;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.Stim;
import org.xper.allen.nafc.blockgen.AbstractTrialGenerator;
import org.xper.rfplot.drawing.GaborSpec;
import org.xper.rfplot.drawing.gabor.IsoGaborSpec;
import org.xper.util.FileUtil;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

public class IsoGaborTrialGenerator extends AbstractTrialGenerator<Stim> {

    private final int numRepeats = 1;
    private GaborSpec gaborSpec;
    public static final List<Double> frequencies = Arrays.asList(0.5, 1.0, 2.0, 4.0);
    public static final List<Double> mixedPhases = Arrays.asList(0.0, 0.25, 0.5, 0.75);
//    public static final List<Double> frequencies = Arrays.asList(4.0);

    public static void main(String[] args) {
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(FileUtil.loadConfigClass("experiment.config_class"), IsoGaborConfig.class);
        IsoGaborTrialGenerator gen = context.getBean(IsoGaborTrialGenerator.class);



        gen.generate();
    }

    @Override
    protected void addTrials() {
        int size = 4;
        int orientation = 45;
        int xCenter = 5;
        int yCenter = 5;
        gaborSpec = new GaborSpec();
        gaborSpec.setOrientation(orientation);
        gaborSpec.setPhase(0);
        gaborSpec.setXCenter(xCenter);
        gaborSpec.setYCenter(yCenter);
        gaborSpec.setSize(size);
        gaborSpec.setAnimation(false);

        // Pure Gabors
        for (Double frequency : frequencies) {
            gaborSpec.setFrequency(frequency);
            addIsochromaticTrials();
            addIsoluminantTrials();
        }

        // Mixed Gabors - frequencies
        for (Double frequencyChromatic : frequencies){
            GaborSpec chromaticSpec = new GaborSpec(gaborSpec);
            chromaticSpec.setFrequency(frequencyChromatic);
            for (Double frequencyLuminance : frequencies) {
                GaborSpec luminanceSpec = new GaborSpec(gaborSpec);
                luminanceSpec.setFrequency(frequencyLuminance);

                IsoGaborSpec rgMixedIsoSpec = new IsoGaborSpec(chromaticSpec, "RedGreen");
                MixedGaborStim rgMixedIsoStim = new MixedGaborStim(this, rgMixedIsoSpec, luminanceSpec);
                getStims().add(rgMixedIsoStim);

                IsoGaborSpec cyMixedIsoSpec = new IsoGaborSpec(chromaticSpec, "CyanYellow");
                MixedGaborStim cyMixedIsoStim = new MixedGaborStim(this, cyMixedIsoSpec, luminanceSpec);
                getStims().add(cyMixedIsoStim);
            }
        }

        //Mixed Gabors - Phases
        for (double frequency: frequencies){
            GaborSpec chromaticSpec = new GaborSpec(gaborSpec);
            chromaticSpec.setFrequency(frequency);
            for (double phase : mixedPhases){
                double phaseLuminance = phase * frequency;

                GaborSpec luminanceSpec = new GaborSpec(gaborSpec);
                luminanceSpec.setFrequency(frequency);
                luminanceSpec.setPhase(phaseLuminance);

                IsoGaborSpec rgMixedIsoSpec = new IsoGaborSpec(gaborSpec, "RedGreen");
                MixedGaborStim rgMixedIsoStim = new MixedGaborStim(this, rgMixedIsoSpec, luminanceSpec);
                getStims().add(rgMixedIsoStim);

                IsoGaborSpec cyMixedIsoSpec = new IsoGaborSpec(gaborSpec, "CyanYellow");
                MixedGaborStim cyMixedIsoStim = new MixedGaborStim(this, cyMixedIsoSpec, luminanceSpec);
                getStims().add(cyMixedIsoStim);
            }
        }
    }

    private void addIsochromaticTrials() {
        IsoGaborSpec spec = new IsoGaborSpec(gaborSpec, "Gray");
        IsoGaborStim stim = new IsoGaborStim(this, spec);
        getStims().add(stim);

        spec = new IsoGaborSpec(gaborSpec, "Red");
        stim = new IsoGaborStim(this, spec);
        getStims().add(stim);

        spec = new IsoGaborSpec(gaborSpec, "Green");
        stim = new IsoGaborStim(this, spec);
        getStims().add(stim);

        spec = new IsoGaborSpec(gaborSpec, "Cyan");
        stim = new IsoGaborStim(this, spec);
        getStims().add(stim);

        spec = new IsoGaborSpec(gaborSpec, "Yellow");
        stim = new IsoGaborStim(this, spec);
        getStims().add(stim);
    }

    private void addIsoluminantTrials() {
        IsoGaborSpec spec = new IsoGaborSpec(gaborSpec, "CyanYellow");
        IsoGaborStim stim = new IsoGaborStim(this, spec);
        getStims().add(stim);

        spec = new IsoGaborSpec(gaborSpec, "RedGreen");
        stim = new IsoGaborStim(this, spec);
        getStims().add(stim);
    }


    @Override
    protected void writeTrials(){
        for (Stim stim : getStims()) {
            stim.writeStim();
            Long stimId = stim.getStimId();
            for (int i = 0; i < numRepeats; i++) {
                long taskId = getGlobalTimeUtil().currentTimeMicros();
                dbUtil.writeTaskToDo(taskId, stimId, -1, genId);
            }
        }
    }
}