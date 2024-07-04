package org.xper.allen.nafc.experiment.juice;

import org.apache.commons.math.FunctionEvaluationException;
import org.apache.commons.math.analysis.UnivariateRealFunction;
import org.xper.Dependency;
import org.xper.allen.nafc.NAFCStim;
import org.xper.allen.nafc.experiment.NAFCExperimentTask;
import org.xper.allen.nafc.experiment.NAFCTrialContext;
import org.xper.allen.nafc.message.ChoiceEventListener;
import org.xper.allen.specs.NAFCStimSpecSpec;
import org.xper.allen.specs.NoisyPngSpec;
import org.xper.juice.Juice;

import java.sql.Timestamp;
import java.util.List;
public class NAFCNoiseScalingNoiseController implements ChoiceEventListener {
    @Dependency
    Juice juice;

    @Dependency
    UnivariateRealFunction noiseRewardFunction;

    private double rewardMultiplier = 1;

    @Override
    public void sampleOn(long timestamp, NAFCTrialContext context) {
        NAFCExperimentTask task = context.getCurrentTask();
        NoisyPngSpec sampleSpec = NoisyPngSpec.fromXml(task.getSampleSpec());

        //Noise Related Reward
        double noiseChance = sampleSpec.getNoiseChance();
        System.err.println("Noise Rate: " + noiseChance);
        try {
            rewardMultiplier = noiseRewardFunction.value(noiseChance);
        } catch (FunctionEvaluationException e){
            System.err.println(e.getMessage());
            System.out.println("Function evaluation failed, rewardMultiplier defaulting to 1");
            rewardMultiplier = 1;
        }

        //4AFC Reward Multiplier
        System.out.println("Choices: " + task.getChoiceSpec().length);
        if (task.getChoiceSpec().length == 3){
            rewardMultiplier = rewardMultiplier * 0.5;
        }

        //Psychometric Reward Multiplier
        NAFCStimSpecSpec stimSpec = NAFCStimSpecSpec.fromXml(task.getStimSpec());
        String stimType = stimSpec.getStimType();
        if (stimType.equals("EStimShapePsychometricTwoByTwoStim")){
            rewardMultiplier = (rewardMultiplier * 2) + 2;
        }
        System.err.println("Reward Multiplier: " + rewardMultiplier);


    }

    private void deliverReward(long timestamp) {
        for (int i = 0; i< Math.floor(rewardMultiplier); i++){
            juice.deliver();
            System.out.println("Multiplier Juice delivered @ " + new Timestamp(timestamp /1000).toString());
        }
        //Remainder Juice if rewardMultiplier is not an integer
        double remainder = rewardMultiplier % 1;
        if (remainder != 0){
            if (Math.random() < remainder){
                System.out.println("Multiplier Juice delivered @ " + new Timestamp(timestamp /1000).toString());
                juice.deliver();
            }
        }
    }

    @Override
    public void choiceSelectionCorrect(long timestamp, int[] rewardList) {
        deliverReward(timestamp);
    }

    @Override
    public void choiceSelectionDefaultCorrect(long timestamp) {
        deliverReward(timestamp);
    }

    @Override
    public void sampleOff(long timestamp) {

    }

    @Override
    public void sampleEyeInHoldFail(long timestamp) {

    }

    @Override
    public void choicesOn(long timestamp, NAFCTrialContext context) {

    }

    @Override
    public void choicesOff(long timestamp) {

    }

    @Override
    public void choiceSelectionEyeFail(long timestamp) {

    }

    @Override
    public void choiceSelectionSuccess(long timestamp, int choice) {

    }



    @Override
    public void choiceSelectionNull(long timestamp) {

    }


    @Override
    public void choiceSelectionIncorrect(long timestamp, int[] rewardList) {

    }

    public Juice getJuice() {
        return juice;
    }

    public void setJuice(Juice juice) {
        this.juice = juice;
    }

    public UnivariateRealFunction getNoiseRewardFunction() {
        return noiseRewardFunction;
    }

    public void setNoiseRewardFunction(UnivariateRealFunction noiseRewardFunction) {
        this.noiseRewardFunction = noiseRewardFunction;
    }
}