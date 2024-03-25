package org.xper.allen.isoluminant;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.monitorlinearization.MonLinConfig;
import org.xper.allen.monitorlinearization.MonLinTrialGenerator;
import org.xper.allen.nafc.blockgen.AbstractTrialGenerator;
import org.xper.rfplot.drawing.GaborSpec;
import org.xper.rfplot.drawing.gabor.IsoGaborSpec;
import org.xper.util.FileUtil;

public class IsoGaborTrialGenerator extends AbstractTrialGenerator<IsoGaborStim> {

    private int numRepeats = 5;

    public static void main(String[] args) {
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(FileUtil.loadConfigClass("experiment.config_class"), IsoGaborConfig.class);
        IsoGaborTrialGenerator gen = context.getBean(IsoGaborTrialGenerator.class);

        gen.generate();
    }

    @Override
    protected void addTrials() {
        addIsoluminantTrials();

    }

    private void addIsoluminantTrials() {
        //TODO: get this information from receptive field mapping
        GaborSpec tempSpec = new GaborSpec();
        tempSpec.setOrientation(45);
        tempSpec.setPhase(0);
        tempSpec.setFrequency(2);
        tempSpec.setXCenter(0);
        tempSpec.setYCenter(0);
        tempSpec.setSize(5);
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



}