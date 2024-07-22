package org.xper.allen.nafc.experiment.juice;

import org.apache.commons.math.FunctionEvaluationException;
import org.apache.commons.math.analysis.UnivariateRealFunction;
import org.xper.Dependency;
import org.xper.allen.nafc.experiment.NAFCExperimentTask;
import org.xper.allen.nafc.experiment.NAFCTrialContext;
import org.xper.allen.nafc.message.ChoiceEventListener;
import org.xper.allen.specs.NoisyPngSpec;
import org.xper.classic.MarkStimTrialDrawingController;
import org.xper.classic.TrialDrawingController;
import org.xper.drawing.Context;
import org.xper.drawing.Drawable;
import org.xper.drawing.GLUtil;
import org.xper.drawing.object.Circle;
import org.xper.drawing.renderer.Renderer;
import org.xper.juice.Juice;
import org.xper.util.ThreadUtil;

import java.sql.Timestamp;

/**
 * Scales reward with difficulty:
 *  noiseChance
 *  number of choices
 *  psychometric reward (disabled)
 *
 *
 *  Scales reward with streaks of correct choices
 */
public class NAFCDynamicNoiseController implements ChoiceEventListener {
    @Dependency
    Juice juice;

    @Dependency
    UnivariateRealFunction noiseRewardFunction;

    @Dependency
    MarkStimTrialDrawingController drawingController;

    @Dependency
    Renderer renderer;

    private double rewardMultiplier = 1;

    //streaks
    private int correctStreak = 0;
    int streakThreshold = 3;
    boolean isStreak = false;

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



//        //Psychometric Reward Multiplier
//        NAFCStimSpecSpec stimSpec = NAFCStimSpecSpec.fromXml(task.getStimSpec());
//        String stimType = stimSpec.getStimType();
//        if (stimType.equals("EStimShapePsychometricTwoByTwoStim")){
//            rewardMultiplier = (rewardMultiplier * 1.5) + 0.75;
//        }

//        // Rand Multiplier Penalty
//        int randCount = 0;
//        for (int i = 0; i < task.getChoiceSpec().length; i++) {
//            NoisyPngSpec choiceSpec = NoisyPngSpec.fromXml(task.getChoiceSpec()[i]);
//            String choicePngPath = choiceSpec.getPngPath();
//            if (choicePngPath.contains("rand")) {
//                randCount++;
//            }
//        }
//
//        int proceduralCount = 4 - randCount;
//        rewardMultiplier = (proceduralCount / 4.0) * rewardMultiplier;
//        rewardMultiplier = Math.max(1, rewardMultiplier);
    }

    private void drawStreak(Context context) {
        Drawable streak = new Drawable() {
            @Override
            public void draw(Context context) {
                GLUtil.drawCircle(new Circle(true, 5), 0, 0, 0,0,255,0);
            }

        };
        renderer.draw(streak, context);
        drawingController.getWindow().swapBuffers();
    }

    private void deliverReward(long timestamp) {
        System.err.println("Reward Multiplier: " + rewardMultiplier);

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
    public void choiceSelectionCorrect(long timestamp, int[] rewardList, Context context) {
        addToStreak();

        //STREAKS
        System.out.println("Correct Streak: " + correctStreak);
        if (isStreak){
            System.out.println("STREAK MULTIPLIER ACTIVATED");
            rewardMultiplier = rewardMultiplier * 2;
        }

        if (isStreak){
            drawStreak(context);
        }
        deliverReward(timestamp);
    }

    private void addToStreak() {
        correctStreak++;
        if (correctStreak >= streakThreshold){
            isStreak = true;
        } else{
            isStreak = false;
        }
    }

    private void resetStreak() {
        correctStreak = 0;
        isStreak = false;
    }

    @Override
    public void choiceSelectionDefaultCorrect(long timestamp) {
        deliverReward(timestamp);
        addToStreak();
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
        resetStreak();
    }


    @Override
    public void choiceSelectionIncorrect(long timestamp, int[] rewardList) {
        resetStreak();
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

    public TrialDrawingController getDrawingController() {
        return drawingController;
    }

    public void setDrawingController(MarkStimTrialDrawingController drawingController) {
        this.drawingController = drawingController;
    }

    public Renderer getRenderer() {
        return renderer;
    }

    public void setRenderer(Renderer renderer) {
        this.renderer = renderer;
    }
}