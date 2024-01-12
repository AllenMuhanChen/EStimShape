package org.xper.allen.nafc.experiment;

import org.xper.Dependency;
import org.xper.classic.Punisher;

public class NAFCPunisher extends Punisher {

    @Dependency
    int sampleHoldFailPunishmentTime;

    public int itiPunishmentTime;

    public void punishSampleHoldFail(){
        itiPunishmentTime = sampleHoldFailPunishmentTime;
    }

    public void resetPunishment() {
        super.resetPunishment();
        itiPunishmentTime = 0;
    }

    public int getSampleHoldFailPunishmentTime() {
        return sampleHoldFailPunishmentTime;
    }

    public void setSampleHoldFailPunishmentTime(int sampleHoldFailPunishmentTime) {
        this.sampleHoldFailPunishmentTime = sampleHoldFailPunishmentTime;
    }
}