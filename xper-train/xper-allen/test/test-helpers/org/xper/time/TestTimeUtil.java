package org.xper.time;

import org.xper.time.TimeUtil;
import org.xper.util.OsUtil;

import java.time.Instant;

public class TestTimeUtil implements TimeUtil {
    public static long testTime;

    public TestTimeUtil() {
        testTime = System.currentTimeMillis()*1000;
    }

    @Override
    public long currentTimeMicros() {
        return testTime;
    }

    public long getTestTime() {
        return testTime;
    }



}
