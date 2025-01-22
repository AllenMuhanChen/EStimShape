package org.xper.allen.pga;

import org.apache.commons.math.FunctionEvaluationException;
import org.apache.commons.math.analysis.UnivariateRealFunction;
import org.xper.Dependency;
import org.xper.classic.TrialEventListener;
import org.xper.classic.vo.TrialContext;
import org.xper.juice.Juice;

import java.sql.Timestamp;

public class StreakJuiceController implements TrialEventListener {

    @Dependency
    Juice juice;

    @Dependency
    UnivariateRealFunction streakRewardFunction; //maps streak to reward amount

    private int currentStreak = 0;

    @Override
    public void trialInit(long timestamp, TrialContext context) {

    }

    @Override
    public void trialStart(long timestamp, TrialContext context) {

    }

    @Override
    public void fixationPointOn(long timestamp, TrialContext context) {

    }

    @Override
    public void initialEyeInFail(long timestamp, TrialContext context) {

    }

    @Override
    public void initialEyeInSucceed(long timestamp, TrialContext context) {

    }

    @Override
    public void eyeInHoldFail(long timestamp, TrialContext context) {

    }

    @Override
    public void fixationSucceed(long timestamp, TrialContext context) {

    }

    @Override
    public void eyeInBreak(long timestamp, TrialContext context) {
        currentStreak = 0;
    }

    @Override
    public void trialComplete(long timestamp, TrialContext context) {
        currentStreak++;
        System.out.println("Streak: " + currentStreak);
        double rewardMultiplier;
        try {
            rewardMultiplier = streakRewardFunction.value(currentStreak);
        } catch (FunctionEvaluationException e) {
            throw new RuntimeException(e);
        }
        System.out.println("Reward Multiplier: " + rewardMultiplier);
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
    public void trialStop(long timestamp, TrialContext context) {

    }

    public Juice getJuice() {
        return juice;
    }

    public void setJuice(Juice juice) {
        this.juice = juice;
    }

    public UnivariateRealFunction getStreakRewardFunction() {
        return streakRewardFunction;
    }

    public void setStreakRewardFunction(UnivariateRealFunction streakRewardFunction) {
        this.streakRewardFunction = streakRewardFunction;
    }
}