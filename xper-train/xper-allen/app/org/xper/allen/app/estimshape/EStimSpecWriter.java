package org.xper.allen.app.estimshape;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.intan.stimulation.ChargeRecoveryDecorator;
import org.xper.allen.util.AllenDbUtil;
import org.xper.intan.stimulation.*;
import org.xper.util.FileUtil;

import java.util.*;

public class EStimSpecWriter {

    /**
     * Given a list of channels, we can apply different conditions of stimulation to all of those channels
     * @param args
     */
    public static void main(String[] args) {
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"));
        AllenDbUtil dbUtil = context.getBean(AllenDbUtil.class);



        List<RHSChannel> channels = new ArrayList<RHSChannel>();
        channels.add(RHSChannel.A025);
        channels.add(RHSChannel.A030);

        // Template Stimulation

        StimulationShape shape = StimulationShape.BiphasicWithInterphaseDelay;
        double d1 = 200.0;
        double d2 = 200.0;
        double dp = 100.0;
        double a1 = 2.5;
        double a2 = 2.5;
        WaveformParameters waveform = new WaveformParameters(
                shape,
                StimulationPolarity.NegativeFirst,
                d1,
                d2,
                dp,
                a1,
                a2
        );

        int postStimRefractoryPeriod = 4000;
        PulseTrainParameters pulseTrainParameters = new PulseTrainParameters(
                PulseRepetition.SinglePulse,
                1,
                10.0,
                postStimRefractoryPeriod,
                TriggerEdgeOrLevel.Level,
                0.0);

        ChargeRecoveryParameters chargeRecoveryParameters = new ChargeRecoveryParameters(
                true,
                0.0,
                (double) postStimRefractoryPeriod
        );

        ChannelEStimParameters channelParams = new ChannelEStimParameters(
                waveform,
                pulseTrainParameters,
                new AmpSettleParameters(),
                chargeRecoveryParameters);


        // Apply Splitting Here?
        List<ChannelEStimParameters> allChannelParams = new ArrayList<>();
        allChannelParams.add(channelParams);
        // TODO: add more here

        // For all sets of conditions we have (not including channel), apply them to our list of channels.
        List<EStimParameters> allEStimParameters = new ArrayList<>();
        for  (ChannelEStimParameters channelParam :  allChannelParams) {
            EStimParameters eStimParameter = new EStimParameters();
            eStimParameter.put(channels, channelParam);
            allEStimParameters.add(eStimParameter);
        }

        // Apply Decorating Here
        List<EStimParameters> decoratedParameters = new ArrayList<>();
        ChargeRecoveryDecorator decorator = new ChargeRecoveryDecorator();

        for (EStimParameters eStimParams : allEStimParameters) {
            EStimParameters decoratedParam = decorator.decorate(eStimParams);
            decoratedParameters.add(decoratedParam);
        }

        // Read current estim obj ids
        List<Long> estimIds = dbUtil.readEStimObjIds();
        Long maxId = estimIds.stream().max(new Comparator<Long>() {
            @Override
            public int compare(Long o1, Long o2) {
                return o1.compareTo(o2);
            }
        }).orElse(0L);


        // +=1 for each new parameter
        Long nextId = maxId + 1;
        for (EStimParameters eStimParams : decoratedParameters) {
            dbUtil.writeEStimObjData(nextId, eStimParams.toXml(), "");
            System.out.println("Wrote EStim Obj with id: " + nextId);
            nextId += 1;
        }

    }
}
