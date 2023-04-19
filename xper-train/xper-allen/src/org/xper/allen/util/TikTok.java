package org.xper.allen.util;

import java.time.Duration;
import java.time.Instant;

public class TikTok {
    private Instant startTime;
    private String message;

    public TikTok(String message) {
        this.message = message;
        start();
    }

    private void start() {
        startTime = Instant.now();
        System.out.println("TikTok: "+ message + ": Started.");
    }

    public void stop() {
        if (startTime == null) {
            System.out.println("Timer hasn't been started yet.");
            return;
        }

        Instant endTime = Instant.now();
        Duration elapsedTime = Duration.between(startTime, endTime);
        long elapsedTimeMillis = elapsedTime.toMillis();
        System.out.println("TikTok: "+ message + ": Elapsed time: " + elapsedTimeMillis + " ms");
    }
}