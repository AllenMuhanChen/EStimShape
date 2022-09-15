package org.xper.time;

import org.xper.XperConfig;
import org.xper.util.OsUtil;

import java.util.ArrayList;
import java.util.List;

/**
 * @author Allen Chen
 *
 * Intended to be used in unit tests:
 *
 * Contains tic toc functionality for measuring speed of operations.
 *
 * Updates XperConfig so DefaultTimeUtil has access to appropiate native libraries
 *
 */
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

}
