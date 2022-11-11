package org.xper.allen.ga3d.blockgen;

import com.sun.org.apache.xerces.internal.impl.xpath.regex.Match;
import org.xper.allen.Trial;
import org.xper.drawing.stick.MatchStick;

public class RandTrial implements Trial {
    @Override
    public void preWrite() {

    }

    @Override
    public void write() {
        MatchStick mStick = new MatchStick();
        mStick.genMatchStickRand();

        //size
        //location
        //color
        //shading
    }

    @Override
    public Long getTaskId() {
        return null;
    }
}
