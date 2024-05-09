package org.xper.allen.drawing.ga;

import org.junit.Before;
import org.junit.Test;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.allen.pga.RFStrategy;
import org.xper.drawing.Coordinates2D;
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
        testMatchStickDrawer.setup(500, 500);
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
        RFMatchStick RFMatchStick = new RFMatchStick(rf, RFStrategy.PARTIALLY_INSIDE);
        RFMatchStick.setProperties(5, "SHADE");
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

    @Test
    public void test_draw_comp_map(){
        RFMatchStick RFMatchStick = new RFMatchStick(new ReceptiveField() {
            double h = 5;
            double k = 5;
            double r = 5;

            {
                for (int i = 0; i < 100; i++) {
                    double angle = 2 * Math.PI * i / 100;
                    outline.add(new Coordinates2D(h + r * Math.cos(angle), k + r * Math.sin(angle)));
                }
            }
            @Override
            public boolean isInRF(double x, double y) {
                return (x- h)*(x- h) + (y- k)*(y- k) < r * r;
            }
        }, RFStrategy.PARTIALLY_INSIDE);
        RFMatchStick.setProperties(10, "SHADE");
        RFMatchStick.genMatchStickRand();

//        testMatchStickDrawer.drawMStick(RFMatchStick);
        testMatchStickDrawer.draw(new Drawable() {
            @Override
            public void draw() {
                RFMatchStick.drawCompMap();
            }
        });

        ThreadUtil.sleep(10000);
    }

    @Test
    public void test_draw_comp_map_completely_inside_rf(){
        RFMatchStick RFMatchStick = new RFMatchStick(new ReceptiveField() {
            double h = 5;
            double k = 5;
            double r = 5;

            {
                center = new Coordinates2D(h, k);
                for (int i = 0; i < 100; i++) {
                    double angle = 2 * Math.PI * i / 100;
                    outline.add(new Coordinates2D(h + r * Math.cos(angle), k + r * Math.sin(angle)));
                }
            }
            @Override
            public boolean isInRF(double x, double y) {
                return (x- h)*(x- h) + (y- k)*(y- k) < r * r;
            }


        }, RFStrategy.COMPLETELY_INSIDE);
        RFMatchStick.setProperties(1, "SHADE");
        RFMatchStick.genMatchStickRand();

//        testMatchStickDrawer.drawMStick(RFMatchStick);
        testMatchStickDrawer.draw(new Drawable() {
            @Override
            public void draw() {
                RFMatchStick.drawCompMap();
            }
        });

        ThreadUtil.sleep(10000);
    }
}