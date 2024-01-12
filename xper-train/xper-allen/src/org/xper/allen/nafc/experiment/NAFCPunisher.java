package org.xper.allen.nafc.experiment;

import org.xper.Dependency;
import org.xper.classic.Punisher;

public class NAFCPunisher extends Punisher {

    @Dependency
    int sampleHoldFailPunishmentTime;

    public int itiPunishmentTime;

    public void punishSampleHoldFail(){
        setItiPunishmentTime(sampleHoldFailPunishmentTime);
    }

    public void resetPunishment() {
        super.resetPunishment();
        setItiPunishmentTime(0);
    }

    public int getSampleHoldFailPunishmentTime() {
        return sampleHoldFailPunishmentTime;
    }

    public void setSampleHoldFailPunishmentTime(int sampleHoldFailPunishmentTime) {
        this.sampleHoldFailPunishmentTime = sampleHoldFailPunishmentTime;
    }

    public int getItiPunishmentTime() {
        return itiPunishmentTime;
    }

    public void setItiPunishmentTime(int itiPunishmentTime) {
        this.itiPunishmentTime = itiPunishmentTime;
    }
}