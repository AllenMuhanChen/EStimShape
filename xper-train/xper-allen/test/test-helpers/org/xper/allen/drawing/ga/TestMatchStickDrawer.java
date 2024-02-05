package org.xper.allen.drawing.ga;

import org.xper.alden.drawing.drawables.Drawable;
import org.xper.drawing.TestDrawingWindow;
import org.xper.drawing.stick.MatchStick;

import static org.junit.Assert.*;

public class TestMatchStickDrawer {
    private TestDrawingWindow window;

    public void setup(){
        window = TestDrawingWindow.createDrawerWindow();
    }

    public void drawMStick(MatchStick mStick){
        window.draw(new Drawable() {
            @Override
            public void draw() {mStick.draw();
            }
        });
    }

    public void draw(Drawable drawable){
        window.draw(drawable);
    }

}