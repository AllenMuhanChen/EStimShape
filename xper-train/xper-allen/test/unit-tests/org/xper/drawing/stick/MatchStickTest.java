package org.xper.drawing.stick;

import org.junit.Test;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.drawing.TestDrawingWindow;
import org.xper.util.ThreadUtil;

public class MatchStickTest {

    private TestDrawingWindow window;

    @Test
    public void test_read_and_smooth() {

        getTestDrawingWindow();

        String pathToMatchStick = "/home/r2_allen/Downloads/000132_spec.xml";
//
//        MatchStick matchStick = new MatchStick();
//        matchStick.setScaleForMAxisShape(1);
//        matchStick.genMatchStickFromFile(pathToMatchStick);
//        drawMStick(matchStick);
//        ThreadUtil.sleep(2000);


        AllenMatchStick allenMatchStick = new AllenMatchStick();
        allenMatchStick.setProperties(1);
        allenMatchStick.genAllenMatchStickFromMatchStickFile(pathToMatchStick);

        drawMStick(allenMatchStick);
        ThreadUtil.sleep(2000);

        AllenMStickSpec allenMStickSpec = new AllenMStickSpec();
        allenMStickSpec.setMStickInfo(allenMatchStick);

        AllenMatchStick newAllenMStick = new AllenMatchStick();
        newAllenMStick.setProperties(1);
        newAllenMStick.genMatchStickFromShapeSpec(allenMStickSpec, new double[]{0,0,0});
        drawMStick(allenMatchStick);
        ThreadUtil.sleep(5000);

    }

    private void getTestDrawingWindow() {
        window = TestDrawingWindow.createDrawerWindow(500, 500);
    }

    private void drawMStick(MatchStick mStick){
        window.draw(new Drawable() {
            @Override
            public void draw() {mStick.draw();
            }
        });
    }

}