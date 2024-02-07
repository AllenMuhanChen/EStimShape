package org.xper.allen.drawing.ga;

import org.junit.Before;
import org.junit.Test;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.drawing.GLUtil;
import org.xper.drawing.object.Circle;
import org.xper.util.ThreadUtil;

public class RFMatchStickTest {

    private TestMatchStickDrawer testMatchStickDrawer;
    private double h;
    private double k;
    private double r;

    @Before
    public void setUp() throws Exception {
        testMatchStickDrawer = new TestMatchStickDrawer();
        testMatchStickDrawer.setup();
        h = 5;
        k = 5;
        r = 10;
    }

    @Test
    public void test() {
        ReceptiveField rf = new ReceptiveField() {
            @Override
            public boolean isInRF(double x, double y) {
                //circle with radius 5 around x,y;
                return (x- h)*(x- h) + (y- k)*(y- k) < r * r;
            }
        };
        RFMatchStick RFMatchStick = new RFMatchStick(rf);
        RFMatchStick.setProperties(10);
        RFMatchStick.genMatchStickRand();

        testMatchStickDrawer.drawMStick(RFMatchStick);
        testMatchStickDrawer.draw(new Drawable() {
            @Override
            public void draw() {
                GLUtil.drawCircle(new Circle(false, r), r, false, h, k, 100);
            }
        });
        ThreadUtil.sleep(10000);
    }
}