package org.xper.allen.drawing.ga;

import org.junit.Before;
import org.junit.Ignore;
import org.junit.Test;
import org.lwjgl.opengl.GL11;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.morph.GrowingMatchStick;
import org.xper.allen.drawing.composition.morph.PruningMatchStick;
import org.xper.allen.drawing.composition.noisy.GaussianNoiseMapper;
import org.xper.allen.pga.RFStrategy;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.util.ThreadUtil;

import java.util.Collections;
import java.util.List;

import static org.junit.Assert.assertEquals;
import static org.xper.allen.pga.RFStrategy.COMPLETELY_INSIDE;

public class GAMatchStickTest {

    String figPath = "/home/connorlab/Documents/xper-test";

    public static final ReceptiveField PARTIAL_RF = new ReceptiveField() {
        double h = 30;
        double k = 30;
        double r = 20;

        {
            center = new Coordinates2D(h, k);
            radius = r;
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
        double h = 50;
        double k = 50;
        double r = 20;

        {
            center = new Coordinates2D(h, k);
            radius = r;
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
    private GaussianNoiseMapper noiseMapper;

    @Before
    public void setUp() throws Exception {
        testMatchStickDrawer = new TestMatchStickDrawer();
        testMatchStickDrawer.setup(500, 500);

        noiseMapper = new GaussianNoiseMapper();
        noiseMapper.setWidth(500);
        noiseMapper.setHeight(500);
        noiseMapper.setBackground(0);
    }

    @Test
    public void test_mstick_writes_rf_strategy_to_spec(){
        GAMatchStick GAMatchStick = genCompleteleyInside();

        AllenMStickSpec spec = new AllenMStickSpec();
        spec.setMStickInfo(GAMatchStick, false);


        assertEquals(COMPLETELY_INSIDE, spec.getRfStrategy());
    }

    @Test
    public void test_loading_spec_works(){
        RGBColor color = new RGBColor(1.0, 0.0, 0.0);
        GAMatchStick parent = new GAMatchStick(COMPLETE_RF, COMPLETELY_INSIDE);
        int maxSizeDiameterDegrees = 3;
        parent.setProperties(maxSizeDiameterDegrees, "SHADE", 1.0);
        parent.setStimColor(color);
        parent.genMatchStickRand();
        testMatchStickDrawer.draw(parent);
        ThreadUtil.sleep(500);
        testMatchStickDrawer.saveImage(figPath + "/base_native");

        AllenMStickSpec parentSpec = new AllenMStickSpec();
        parentSpec.setMStickInfo(parent, false);
        GAMatchStick parentFromSpec = new GAMatchStick();
        parentFromSpec.setProperties(maxSizeDiameterDegrees, "SHADE", 1.0);
        parentFromSpec.setStimColor(color);
        parentFromSpec.genMatchStickFromShapeSpec(parentSpec, new double[]{0,0,0});
        testMatchStickDrawer.draw(parentFromSpec);
        ThreadUtil.sleep(500);
        testMatchStickDrawer.saveImage(figPath + "/base_from_spec");


    }

    @Test
    public void draw_from_comp_mstick(){
        RGBColor color = new RGBColor(1.0, 0.0, 0.0);

        GAMatchStick parent = new GAMatchStick(COMPLETE_RF, COMPLETELY_INSIDE);
        parent.PARAM_nCompDist = new double[]{0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0};
        double maxSizeDiameterDegrees = 3.5;
        parent.setProperties(maxSizeDiameterDegrees, "SHADE", 1.0);
        parent.setStimColor(color);
        parent.genMatchStickRand();

        AllenMStickSpec parentSpec = new AllenMStickSpec();
        parentSpec.setMStickInfo(parent, false);
        for (int i = 1; i<=parent.getnComponent(); i++){
            System.out.println("Parent component before draw " + parent.getComp()[i].getMassCenter());
        }

        GAMatchStick parentFromSpec = new GAMatchStick();
        parentFromSpec.setProperties(maxSizeDiameterDegrees, "SHADE", 1.0);
        parentFromSpec.setStimColor(color);
        parentFromSpec.genMatchStickFromShapeSpec(parentSpec, new double[]{0,0,0});

        testMatchStickDrawer.draw(parentFromSpec);
        testMatchStickDrawer.saveImage(figPath + "/base_mstick.png");

        ThreadUtil.sleep(1000);
        testMatchStickDrawer.clear();

//        testMatchStickDrawer.draw(parent);
        testMatchStickDrawer.drawCompMap(parent);
        testMatchStickDrawer.saveImage(figPath + "/base_mstick_comp_map.png");
        ThreadUtil.sleep(1000);
        testMatchStickDrawer.clear();

        PruningMatchStick from_comp = null;
        List<Integer> compsToPreserve = Collections.emptyList();
        while (true) {
            try {
                from_comp = new PruningMatchStick(noiseMapper);
                from_comp.setMaxTotalAttempts(15);
                from_comp.setProperties(maxSizeDiameterDegrees, "SHADE", 1.0);
                from_comp.setStimColor(color);

                compsToPreserve = PruningMatchStick.chooseRandomComponentsToPreserve(1, parentFromSpec);
                from_comp.genMatchStickFromComponentsInNoise(parentFromSpec,
                        compsToPreserve,
                        4,
                        true,
                        15);
                break;
            } catch(Exception e) {
                e.printStackTrace();
            }

        }
        testMatchStickDrawer.draw(from_comp);

        testMatchStickDrawer.saveImage(figPath + "/from_comp_1.png");
        ThreadUtil.sleep(1000);
        testMatchStickDrawer.drawCompMap(from_comp);
        testMatchStickDrawer.saveImage(figPath + "/from_comp_1_map.png");
        ThreadUtil.sleep(1000);
        testMatchStickDrawer.saveNoiseMap(figPath + "/from_comp_1_noisemap.png",
                from_comp,
                0.5, from_comp.getPreservedComps()
        );
        System.out.println(from_comp.getMorphData().toXml());
    }

    @Test
    public void draw_pruning_mstick(){
        RGBColor color = new RGBColor(1.0, 0.0, 0.0);

        GAMatchStick parent = new GAMatchStick(COMPLETE_RF, COMPLETELY_INSIDE);
        parent.PARAM_nCompDist = new double[]{0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0};
        int maxSizeDiameterDegrees = 3;
        parent.setProperties(maxSizeDiameterDegrees, "SHADE", 1.0);
        parent.setStimColor(color);
        parent.genMatchStickRand();

        AllenMStickSpec parentSpec = new AllenMStickSpec();
        parentSpec.setMStickInfo(parent, false);
        for (int i = 1; i<=parent.getnComponent(); i++){
            System.out.println("Parent component before draw " + parent.getComp()[i].getMassCenter());
        }

        GAMatchStick parentFromSpec = new GAMatchStick();
        parentFromSpec.setProperties(maxSizeDiameterDegrees, "SHADE", 1.0);
        parentFromSpec.setStimColor(color);
        parentFromSpec.genMatchStickFromShapeSpec(parentSpec, new double[]{0,0,0});

        testMatchStickDrawer.draw(parentFromSpec);
        testMatchStickDrawer.saveImage(figPath + "/base_mstick.png");

        ThreadUtil.sleep(1000);
        testMatchStickDrawer.clear();

//        testMatchStickDrawer.draw(parent);
        testMatchStickDrawer.drawCompMap(parent);
        testMatchStickDrawer.saveImage(figPath + "/base_mstick_comp_map.png");
        ThreadUtil.sleep(1000);
        testMatchStickDrawer.clear();

        PruningMatchStick pruning = null;
        List<Integer> compsToPreserve = Collections.emptyList();
        while (true) {
            try {
                pruning = new PruningMatchStick(noiseMapper);
                pruning.setMaxTotalAttempts(15);
                pruning.setProperties(maxSizeDiameterDegrees, "SHADE", 1.0);
                pruning.setStimColor(color);

                compsToPreserve = PruningMatchStick.chooseRandomComponentsToPreserve(1, parentFromSpec);
                pruning.genPruningMatchStick(parentFromSpec, 0.75, compsToPreserve, null);
                break;
            } catch(Exception e) {
                e.printStackTrace();
            }
        }
        testMatchStickDrawer.draw(pruning);

        testMatchStickDrawer.saveImage(figPath + "/prune_1.png");
        ThreadUtil.sleep(1000);
        testMatchStickDrawer.drawCompMap(pruning);
        testMatchStickDrawer.saveImage(figPath + "/prune_1_comp_map.png");
        ThreadUtil.sleep(1000);
        testMatchStickDrawer.saveNoiseMap(figPath + "/prune_1_noisemap.png",
                pruning,
                0.5, compsToPreserve
                );
        System.out.println(pruning.getMorphData().toXml());
    }

    @Test
    public void draws_mstick_from_file_with_assigned_compId(){
        GAMatchStick complete = new GAMatchStick(PARTIAL_RF, COMPLETELY_INSIDE);
        complete.setProperties(2.5, "SHADE", 1.0);
        complete.genMatchStickRand();


//        testMatchStickDrawer.drawMStick(complete);
//        testMatchStickDrawer.drawCompMap(complete);


        AllenMStickSpec spec = new AllenMStickSpec();
        spec.setMStickInfo(complete, false);
        ThreadUtil.sleep(1000);

        GAMatchStick partial = new GAMatchStick(PARTIAL_RF, RFStrategy.PARTIALLY_INSIDE);
//        partial.setProperties(2.5, "2D");
//        partial.setStimColor(new RGBColor(1.0, 1.0, 0));
        partial.setProperties(2.5, "SHADE", 1.0);
        RGBColor color = new RGBColor(1.0, 0.0, 0.0);
        partial.setStimColor(color);
        partial.genMatchStickFromShapeSpec(spec, new double[]{0,0,0}, spec.getmAxis().getSpecialEndComp());
        partial.setRfStrategy(RFStrategy.PARTIALLY_INSIDE);
        partial.positionShape();

        testMatchStickDrawer.drawMStick(partial);
        double averageContrast = testMatchStickDrawer.calculateAverageContrast(partial);
        System.out.println("Average contrast: " + averageContrast);


        partial.setProperties(2.5, "2D", averageContrast);
        partial.setStimColor(color);
        partial.genMatchStickFromShapeSpec(spec, new double[]{0,0,0}, spec.getmAxis().getSpecialEndComp());
        partial.setRfStrategy(RFStrategy.PARTIALLY_INSIDE);
        partial.positionShape();

        testMatchStickDrawer.drawThumbnail(partial);


//        testMatchStickDrawer.drawCompMap(partial);
//        testMatchStickDrawer.drawThumbnail(partial);

        ThreadUtil.sleep(10000);

    }

    @Test
    public void test_draw_thumbnail() {
        GAMatchStick GAMatchStick = genPartiallyInside();
//        testMatchStickDrawer.drawMStick(GAMatchStick);
        testMatchStickDrawer.drawThumbnail(GAMatchStick);
        ThreadUtil.sleep(10000);

    }

    @Test
    public void test_draw_comp_map_partially_inside_rf(){
        GAMatchStick GAMatchStick = genPartiallyInside();

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

            growingMatchStick.setProperties(4, "SHADE", 1.0);
            try {
                growingMatchStick.genInsideRFMorphedMStick(GAMatchStick, 0.2);
                break;
            } catch (Exception e) {
                e.printStackTrace();
            }

        }
        testMatchStickDrawer.drawMStick(growingMatchStick);
        testMatchStickDrawer.drawCompMap(growingMatchStick);
        System.out.println(growingMatchStick.getMorphData().toXml());
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

            growingMatchStick.setProperties(4, "SHADE", 1.0);
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

            growingMatchStick.setProperties(2.5, "SHADE", 1.0);
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

    @Ignore
    @Test
    public void fig_examples_of_inside_vs_outside_morphs(){
        GAMatchStick baseMatchStick = genPartiallyInside();
        testMatchStickDrawer.drawMStick(baseMatchStick);
        testMatchStickDrawer.drawRF(baseMatchStick);
        testMatchStickDrawer.saveImage(figPath + "/base_mstick.png");
        ThreadUtil.sleep(1000);
        testMatchStickDrawer.clear();
        GrowingMatchStick inside;
        while (true) {
            inside = new GrowingMatchStick(PARTIAL_RF, RFStrategy.PARTIALLY_INSIDE);

            inside.setProperties(5, "SHADE", 1.0);
            try {
                inside.genInsideRFMorphedMStick(baseMatchStick, 0.7);
                break;
            } catch (Exception e) {
                e.printStackTrace();
            }

        }
        testMatchStickDrawer.drawMStick(inside);
        testMatchStickDrawer.drawRF(inside);
        testMatchStickDrawer.saveImage(figPath + "/inside_morph.png");
        testMatchStickDrawer.clear();

        GrowingMatchStick outside;
        while (true) {
            outside = new GrowingMatchStick(PARTIAL_RF, RFStrategy.PARTIALLY_INSIDE);

            outside.setProperties(5, "SHADE", 1.0);
            try {
                outside.genOutsideRFMorphedMStick(baseMatchStick, 0.4);
                break;
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        testMatchStickDrawer.drawMStick(outside);
        testMatchStickDrawer.saveImage(figPath + "/outside_morph.png");
        testMatchStickDrawer.clear();

        GrowingMatchStick both;
        while (true) {
            both = new GrowingMatchStick(PARTIAL_RF, RFStrategy.PARTIALLY_INSIDE);

            both.setProperties(5, "SHADE", 1.0);
            try {
                both.genOutsideRFMorphedMStick(baseMatchStick, 0.7);
                both.genInsideRFMorphedMStick(both, 0.4);
                break;
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        testMatchStickDrawer.drawMStick(both);
        testMatchStickDrawer.drawRF(both);
        testMatchStickDrawer.saveImage(figPath + "/both_morph.png");
        ThreadUtil.sleep(10000);
    }

    @Ignore
    @Test
    public void fig_examples_of_diff_mutation_magnitudes(){
        GAMatchStick baseMatchStick = genPartiallyInside();
        testMatchStickDrawer.drawMStick(baseMatchStick);
        testMatchStickDrawer.saveImage(figPath + "/base_mstick.png");
        ThreadUtil.sleep(1000);
        testMatchStickDrawer.clear();
        GrowingMatchStick low;
        while (true) {
            low = new GrowingMatchStick(PARTIAL_RF, RFStrategy.PARTIALLY_INSIDE);

            low.setProperties(2.5, "SHADE", 1.0);
            try {
                low.genOutsideRFMorphedMStick(baseMatchStick, 0.1);
                break;
            } catch (Exception e) {
                e.printStackTrace();
            }

        }

        testMatchStickDrawer.drawMStick(low);
        testMatchStickDrawer.saveImage(figPath + "/low_morph.png");
        testMatchStickDrawer.clear();

        GrowingMatchStick mid;
        while (true) {
            mid = new GrowingMatchStick(PARTIAL_RF, RFStrategy.PARTIALLY_INSIDE);

            mid.setProperties(2.5, "SHADE", 1.0);
            try {
                mid.genOutsideRFMorphedMStick(baseMatchStick, 0.4);
                break;
            } catch (Exception e) {
                e.printStackTrace();
            }

        }

        testMatchStickDrawer.drawMStick(mid);
        testMatchStickDrawer.saveImage(figPath + "/mid_morph.png");
        testMatchStickDrawer.clear();

        GrowingMatchStick high;
        while (true) {
            high = new GrowingMatchStick(PARTIAL_RF, RFStrategy.PARTIALLY_INSIDE);

            high.setProperties(2.5, "SHADE", 1.0);
            try {
                high.genOutsideRFMorphedMStick(baseMatchStick, 0.7);
                break;
            } catch (Exception e) {
                e.printStackTrace();
            }
        }

        testMatchStickDrawer.drawMStick(high);
        testMatchStickDrawer.saveImage(figPath + "/high_morph.png");

    }


    private static GAMatchStick genPartiallyInside() {
        GAMatchStick GAMatchStick = new GAMatchStick(PARTIAL_RF, RFStrategy.PARTIALLY_INSIDE);
        GAMatchStick.setProperties(4, "SHADE", 1.0);
        GAMatchStick.genMatchStickRand();
        return GAMatchStick;
    }

    private static GAMatchStick genCompleteleyInside() {
        GAMatchStick GAMatchStick = new GAMatchStick(COMPLETE_RF, COMPLETELY_INSIDE);
        GAMatchStick.setProperties(2.5, "SHADE", 1.0);
        GAMatchStick.genMatchStickRand();
        return GAMatchStick;
    }

    @Test
    public void testPartialMStickData(){
        GAMatchStick GAMatchStick = genPartiallyInside();
        AllenMStickData mStickData = (AllenMStickData) GAMatchStick.getMStickData();

        testMatchStickDrawer.drawMStick(GAMatchStick);
        GL11.glDisable(GL11.GL_DEPTH_TEST);
        testMatchStickDrawer.drawMassCenter(mStickData);


        GL11.glMatrixMode(GL11.GL_MODELVIEW);
        GL11.glPushMatrix(); // Save the current matrix
        // Translate the drawing by the mass center
        GL11.glTranslatef((float) mStickData.getMassCenter().x, (float) mStickData.getMassCenter().y, (float) mStickData.getMassCenter().z);
        testMatchStickDrawer.drawMStickData(GAMatchStick, mStickData);
        GL11.glPopMatrix(); // Restore the original matrix


        ThreadUtil.sleep(10000);

    }
}