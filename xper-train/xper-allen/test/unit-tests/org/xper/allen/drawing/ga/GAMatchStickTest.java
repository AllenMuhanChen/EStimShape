package org.xper.allen.drawing.ga;

import org.junit.Before;
import org.junit.Test;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.morph.GrowingMatchStick;
import org.xper.allen.pga.RFStrategy;
import org.xper.drawing.Coordinates2D;
import org.xper.util.ThreadUtil;

import static org.junit.Assert.assertEquals;

public class GAMatchStickTest {

    public static final ReceptiveField PARTIAL_RF = new ReceptiveField() {
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
            return (x - h) * (x - h) + (y - k) * (y - k) < r * r;
        }
    };
    public static final ReceptiveField COMPLETE_RF = new ReceptiveField() {
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
            return (x - h) * (x - h) + (y - k) * (y - k) < r * r;
        }
    };
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
    public void draws_mstick_from_file_with_assigned_compId(){
        GAMatchStick complete = new GAMatchStick(PARTIAL_RF, RFStrategy.COMPLETELY_INSIDE, "SHADE");
        complete.setProperties(2.5, "SHADE");
        complete.genMatchStickRand();


        testMatchStickDrawer.drawMStick(complete);
        testMatchStickDrawer.drawCompMap(complete);


        AllenMStickSpec spec = new AllenMStickSpec();
        spec.setMStickInfo(complete, false);
        ThreadUtil.sleep(1000);

        GAMatchStick partial = new GAMatchStick(PARTIAL_RF, RFStrategy.PARTIALLY_INSIDE, "SHADE");
        partial.setProperties(2.5, "SHADE");
        partial.genMatchStickFromShapeSpec(spec, new double[]{0,0,0}, spec.getmAxis().getSpecialEndComp());

        testMatchStickDrawer.drawMStick(partial);
        testMatchStickDrawer.drawCompMap(partial);
        ThreadUtil.sleep(10000);

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

    @Test
    public void test_inside_rf_morph(){
        GAMatchStick GAMatchStick = genPartiallyInside();
        testMatchStickDrawer.drawMStick(GAMatchStick);
        testMatchStickDrawer.drawCompMap(GAMatchStick);
        ThreadUtil.sleep(1000);
        testMatchStickDrawer.clear();
        GrowingMatchStick growingMatchStick;
        while (true) {
            growingMatchStick = new GrowingMatchStick(PARTIAL_RF, RFStrategy.PARTIALLY_INSIDE);

            growingMatchStick.setProperties(2.5, "SHADE");
            try {
                growingMatchStick.genInsideRFMorphedMStick(GAMatchStick, 0.2);
                break;
            } catch (Exception e) {
                e.printStackTrace();
            }

        }
        testMatchStickDrawer.drawMStick(growingMatchStick);
        testMatchStickDrawer.drawCompMap(growingMatchStick);
        ThreadUtil.sleep(10000);
    }

    @Test
    public void test_outside_rf_morph(){
        GAMatchStick GAMatchStick = genPartiallyInside();
        testMatchStickDrawer.drawMStick(GAMatchStick);
        testMatchStickDrawer.drawCompMap(GAMatchStick);
        ThreadUtil.sleep(1000);
        testMatchStickDrawer.clear();
        GrowingMatchStick growingMatchStick;
        while (true) {
            growingMatchStick = new GrowingMatchStick(PARTIAL_RF, RFStrategy.PARTIALLY_INSIDE);

            growingMatchStick.setProperties(2.5, "SHADE");
            try {
                growingMatchStick.genOutsideRFMorphedMStick(GAMatchStick, 0.2);
                break;
            } catch (Exception e) {
                e.printStackTrace();
            }

        }
        testMatchStickDrawer.drawMStick(growingMatchStick);
        testMatchStickDrawer.drawCompMap(growingMatchStick);
        ThreadUtil.sleep(10000);
    }

    @Test
    public void test_both_inside_and_outside_morph(){
        GAMatchStick GAMatchStick = genPartiallyInside();
        testMatchStickDrawer.drawMStick(GAMatchStick);
        testMatchStickDrawer.drawCompMap(GAMatchStick);
        ThreadUtil.sleep(1000);
        testMatchStickDrawer.clear();
        GrowingMatchStick growingMatchStick;
        while (true) {
            growingMatchStick = new GrowingMatchStick(PARTIAL_RF, RFStrategy.PARTIALLY_INSIDE);

            growingMatchStick.setProperties(2.5, "SHADE");
            try {
                growingMatchStick.genOutsideRFMorphedMStick(GAMatchStick, 0.2);
                growingMatchStick.genInsideRFMorphedMStick(growingMatchStick, 0.2);
                break;
            } catch (Exception e) {
                e.printStackTrace();
            }

        }
        testMatchStickDrawer.drawMStick(growingMatchStick);
        testMatchStickDrawer.drawCompMap(growingMatchStick);
        ThreadUtil.sleep(10000);
    }


    private static GAMatchStick genPartiallyInside() {
        GAMatchStick GAMatchStick = new GAMatchStick(PARTIAL_RF, RFStrategy.PARTIALLY_INSIDE, "SHADE");
        GAMatchStick.setProperties(2.5, "SHADE");
        GAMatchStick.genMatchStickRand();
        return GAMatchStick;
    }

    private static GAMatchStick genCompleteleyInside() {
        GAMatchStick GAMatchStick = new GAMatchStick(COMPLETE_RF, RFStrategy.COMPLETELY_INSIDE, "SHADE");
        GAMatchStick.setProperties(2.5, "SHADE");
        GAMatchStick.genMatchStickRand();
        return GAMatchStick;
    }
}