package org.xper.classic;

import org.xper.Dependency;
import org.xper.drawing.object.FixationPoint;

public class Punisher {
    @Dependency
    int punishmentDelayTime; //Gets initialized to 0, if punishment should be applied, it's incremented, reset to zero after trial interval.@org.xper.Dependency
    @Dependency
    int streakToStartPunishment = 3; //how many times punish() needs to be called to trigger a punishment delay//Local vars for punishment
    @Dependency
    FixationPoint punishmentFixationPoint;


    private int currentStreakForPunishment = 0;
    public int currentPunishmentTime;

    /**
     * 0 if the monkey should not be punished
     * punishmentDelayTime if they should be punished
     * @return
     */
    public int getCurrentPunishmentTime() {
        return currentPunishmentTime;
    }

    public void resetPunishment() {
        currentStreakForPunishment = 0;
        this.setCurrentPunishmentTime(0);
    }

    public void punish() {
        currentStreakForPunishment++;
        if (currentStreakForPunishment >= streakToStartPunishment) {
            this.setCurrentPunishmentTime(punishmentDelayTime);
        }
        this.setCurrentPunishmentTime(0);
    }

    public void setCurrentPunishmentTime(int currentPunishmentTime) {
        this.currentPunishmentTime = currentPunishmentTime;
    }

    public void setPunishmentDelayTime(int punishmentDelayTime) {
        this.punishmentDelayTime = punishmentDelayTime;
    }

    public void setStreakToStartPunishment(int streakToStartPunishment) {
        this.streakToStartPunishment = streakToStartPunishment;
    }

    public FixationPoint getPunishmentFixationPoint() {
        return punishmentFixationPoint;
    }

    public void setPunishmentFixationPoint(FixationPoint punishmentFixationPoint) {
        this.punishmentFixationPoint = punishmentFixationPoint;
    }

}