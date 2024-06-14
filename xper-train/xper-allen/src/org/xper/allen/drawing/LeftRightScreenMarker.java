package org.xper.allen.drawing;

import org.xper.drawing.object.AlternatingScreenMarker;

/**
 * A screen marker with explicit control over whether marker is left or right
 */
public class LeftRightScreenMarker extends AlternatingScreenMarker {
    public void left(){
        i=2;
    }
    public void right(){
        i=3;
        System.out.println("Right");
    }

    @Override
    public void next() {
        //Do nothing
    }
}