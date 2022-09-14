package org.xper.time;

import org.xper.XperConfig;
import org.xper.util.OsUtil;

import java.util.ArrayList;
import java.util.List;

public class TestingTimeUtil extends DefaultTimeUtil {
    private long tic;
    private long toc;
    private long elapsed;

    static {
        List<String> libs = new ArrayList<String>();
        libs.add("xper");
        new XperConfig("", libs);
    }

    public void tic(){
        this.tic = currentTimeMicros();
        this.toc = 0;
    }

    public void toc(){
        this.toc = currentTimeMicros();
        this.elapsed = toc-tic;
    }

    public long elapsedTimeMicros(){
        return elapsed;
    }

    public int elapsedTimeMillis(){
        return Math.round(elapsed/1000);
    }

    public long currentTimeMicros() {
        long next = OsUtil.getTimeOfDay();
        return next;
    }
}
