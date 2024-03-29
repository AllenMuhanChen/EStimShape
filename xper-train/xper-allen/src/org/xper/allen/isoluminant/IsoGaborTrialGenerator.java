package org.xper.allen.isoluminant;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.nafc.blockgen.AbstractTrialGenerator;
import org.xper.rfplot.drawing.GaborSpec;
import org.xper.rfplot.drawing.gabor.IsoGaborSpec;
import org.xper.util.FileUtil;

import java.util.Collections;

public class IsoGaborTrialGenerator extends AbstractTrialGenerator<IsoGaborStim> {

    private int numRepeats = 1;

    public static void main(String[] args) {
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(FileUtil.loadConfigClass("experiment.config_class"), IsoGaborConfig.class);
        IsoGaborTrialGenerator gen = context.getBean(IsoGaborTrialGenerator.class);

        gen.generate();
    }

    @Override
    protected void addTrials() {
        addIsochromaticTrials();
        addRedGreenIsoluminantTrials();
        addCyanYellowIsoluminantTrials();
    }

    private void addIsochromaticTrials() {
        GaborSpec tempSpec = new GaborSpec();
        tempSpec.setOrientation(45);
        tempSpec.setPhase(0);
        tempSpec.setFrequency(0.5);
        tempSpec.setXCenter(0);
        tempSpec.setYCenter(0);
        tempSpec.setSize(20);
        tempSpec.setAnimation(false);

        IsoGaborSpec spec = new IsoGaborSpec(tempSpec, "Red");
        IsoGaborStim stim = new IsoGaborStim(this, spec);
        getStims().add(stim);

        spec = new IsoGaborSpec(tempSpec, "Green");
        stim = new IsoGaborStim(this, spec);
        getStims().add(stim);

        spec = new IsoGaborSpec(tempSpec, "Cyan");
        stim = new IsoGaborStim(this, spec);
        getStims().add(stim);

        spec = new IsoGaborSpec(tempSpec, "Yellow");
        stim = new IsoGaborStim(this, spec);
        getStims().add(stim);
    }

    private void addCyanYellowIsoluminantTrials() {
        //TODO: get this information from receptive field mapping
        GaborSpec tempSpec = new GaborSpec();
        tempSpec.setOrientation(45);
        tempSpec.setPhase(0);
        tempSpec.setFrequency(0.5);
        tempSpec.setXCenter(0);
        tempSpec.setYCenter(0);
        tempSpec.setSize(20);
        tempSpec.setAnimation(false);

        IsoGaborSpec spec = new IsoGaborSpec(tempSpec, "CyanYellow");
        IsoGaborStim stim = new IsoGaborStim(this, spec);
        getStims().add(stim);
    }

    private void addRedGreenIsoluminantTrials() {
        //TODO: get this information from receptive field mapping
        GaborSpec tempSpec = new GaborSpec();
        tempSpec.setOrientation(45);
        tempSpec.setPhase(0);
        tempSpec.setFrequency(0.5);
        tempSpec.setXCenter(0);
        tempSpec.setYCenter(0);
        tempSpec.setSize(20);
        tempSpec.setAnimation(false);

        IsoGaborSpec spec = new IsoGaborSpec(tempSpec, "RedGreen");
        IsoGaborStim stim = new IsoGaborStim(this, spec);
        getStims().add(stim);
    }

    @Override
    protected void writeTrials(){
        for (IsoGaborStim stim : getStims()) {
            stim.writeStim();
            Long stimId = stim.getStimId();
            for (int i = 0; i < numRepeats; i++) {
                long taskId = getGlobalTimeUtil().currentTimeMicros();
                dbUtil.writeTaskToDo(taskId, stimId, -1, genId);
            }
        }
    }

    protected void shuffleTrials() {
//        Collections.shuffle(getStims());
    }



}