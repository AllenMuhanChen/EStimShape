package org.xper.allen.drawing.ga;

import org.junit.Before;
import org.junit.Test;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.pga.RFStrategy;
import org.xper.drawing.Coordinates2D;
import org.xper.util.ThreadUtil;

import static org.junit.Assert.assertEquals;

public class GAMatchStickTest {

    private TestMatchStickDrawer testMatchStickDrawer;

    @Before
    public void setUp() throws Exception {
        testMatchStickDrawer = new TestMatchStickDrawer();
        testMatchStickDrawer.setup(500, 500);

    }

    @Test
    public void test_mstick_writes_rf_strategy_to_spec(){
        GAMatchStick GAMatchStick = genCompleteleyInside();

        AllenMStickSpec spec = new AllenMStickSpec();
        spec.setMStickInfo(GAMatchStick, false);


        assertEquals(RFStrategy.COMPLETELY_INSIDE, spec.getRfStrategy());
    }

    @Test
    public void test_draw_comp_map_partially_inside_rf(){
        GAMatchStick GAMatchStick = genPartiallyInside();

        testMatchStickDrawer.drawMStick(GAMatchStick);

        ThreadUtil.sleep(100);

        testMatchStickDrawer.draw(new Drawable() {
            @Override
            public void draw() {
                GAMatchStick.drawCompMap();
            }
        });

        ThreadUtil.sleep(10000);
    }

    @Test
    public void test_draw_comp_map_completely_inside_rf(){
        GAMatchStick GAMatchStick = genCompleteleyInside();

        testMatchStickDrawer.drawMStick(GAMatchStick);

        ThreadUtil.sleep(1000);

        testMatchStickDrawer.draw(new Drawable() {
            @Override
            public void draw() {
                GAMatchStick.drawCompMap();
            }
        });

        ThreadUtil.sleep(10000);
    }

    private static GAMatchStick genPartiallyInside() {
        GAMatchStick GAMatchStick = new GAMatchStick(new ReceptiveField() {
            double h = 20;
            double k = 20;
            double r = 10;
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
        }, RFStrategy.PARTIALLY_INSIDE);
        GAMatchStick.setProperties(2.5, "SHADE");
        GAMatchStick.genMatchStickRand();
        return GAMatchStick;
    }

    private static GAMatchStick genCompleteleyInside() {
        GAMatchStick GAMatchStick = new GAMatchStick(new ReceptiveField() {
            double h = 20;
            double k = 30;
            double r = 10;
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
        GAMatchStick.setProperties(2.5, "SHADE");
        GAMatchStick.genMatchStickRand();
        return GAMatchStick;
    }
}