package org.xper.allen.drawing.composition.experiment;

import org.junit.Before;
import org.junit.Test;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.allen.drawing.composition.AllenMAxisArc;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.morph.ComponentMorphParameters;
import org.xper.allen.drawing.composition.morph.RadiusInfo;
import org.xper.allen.drawing.composition.morph.RadiusProfile;
import org.xper.allen.drawing.ga.TestMatchStickDrawer;
import org.xper.allen.noisy.NoisyTranslatableResizableImages;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.drawing.renderer.PerspectiveRenderer;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.util.ThreadUtil;

import javax.vecmath.Vector3d;
import java.awt.*;
import java.util.LinkedHashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;

public class DepthLightingPostHocMatchStickTest {

    public static final int TIME = 1000;
    private TestMatchStickDrawer drawer;
    private String figurePath;

    @Before
    public void setUp() throws Exception {
        drawer = new TestMatchStickDrawer();
        drawer.setup(190, 190);

        figurePath = "/home/r2_allen/git/EStimShape/plots/grant_240212";


    }

    @Test
    public void test_countours() {
        //potential good base mSticks
        //1702588420352043_sample
        //1702588489214206_sample

        String filename = "/home/r2_allen/git/EStimShape/xper-train/stimuli/procedural/specs/1702588489214206_spec.xml";
        DepthLightingPostHocMatchStick baseMStick = new DepthLightingPostHocMatchStick();
        baseMStick.setProperties(12, "SHADE");
        baseMStick.setTextureType("2D");
        baseMStick.genMatchStickFromFile(filename);

        drawer.drawGhost(baseMStick);
        ThreadUtil.sleep(TIME);

        DepthLightingPostHocMatchStick flippedStick = new DepthLightingPostHocMatchStick();
        flippedStick.setProperties(12, "SHADE");
        flippedStick.setTextureType("2D");
        int componentId = 1;
        flippedStick.genFlippedMatchStick(baseMStick, componentId);

//        drawer.clear();
        drawer.drawGhost(flippedStick);
        ThreadUtil.sleep(TIME);
    }

    @Test
    public void make_figs_for_angles_at_4_lightings(){
        float[][] lightPositions = new float[][]{
                {0.0f, 354.0f, 354.0f, 1.0f},
                {0.0f, -354.0f, 354.0f, 1.0f},
                {354.0f, 0.0f, 354.0f, 1.0f},
                {-354.0f, 0.0f, 354.0f, 1.0f},
        };

        String filename = "/home/r2_allen/git/EStimShape/plots/grant_240212/shape_variations/saved/bespoke/original_angle_spec_spec.xml";
        DepthLightingPostHocMatchStick baseMStick = new DepthLightingPostHocMatchStick();
        baseMStick.setProperties(12, "SHADE");
        baseMStick.genMatchStickFromFile(filename);
        int index=0;
        for (float[] lightPosition : lightPositions) {
            baseMStick.light_position = lightPosition;
            drawer.clear();
            drawer.drawMStick(baseMStick);
            drawer.saveImage(figurePath + "/lighting_variations" + "/original_angle_with_lighting_" + index);
            ThreadUtil.sleep(TIME);
            index++;
        }


        DepthLightingPostHocMatchStick flippedStick = new DepthLightingPostHocMatchStick();
        flippedStick.setProperties(12, "SHADE");
        int componentId = 1;
        flippedStick.genFlippedMatchStick(baseMStick, componentId);

        index=0;
        for (float[] lightPosition : lightPositions) {
            flippedStick.light_position = lightPosition;
            drawer.clear();
            drawer.drawMStick(flippedStick);
            drawer.saveImage(figurePath + "/lighting_variations" + "/flipped_angle_with_lighting_" + index);
            ThreadUtil.sleep(TIME);
            index++;
        }
    }

    @Test
    public void make_figs_for_3_shape_variations_for_angles(){
        List<DepthLightingPostHocMatchStick> originalAngleMSticks = new LinkedList<>();
        int numShapeVariations = 2;

        //GENERATE SHAPE VARIATIONS
        String filename = "/home/r2_allen/git/EStimShape/xper-train/stimuli/procedural/specs/1702588489214206_spec.xml";
        String shapeVariationsPath = figurePath + "/shape_variations";
        DepthLightingPostHocMatchStick baseMStick = new DepthLightingPostHocMatchStick();
        baseMStick.setProperties(12, "SHADE");
        baseMStick.genMatchStickFromFile(filename);
        originalAngleMSticks.add(baseMStick);

        for (int i=0; i<numShapeVariations; i++) {
            DepthLightingPostHocMatchStick newMStick = new DepthLightingPostHocMatchStick();
            newMStick.setProperties(12, "SHADE");
            newMStick.genMorphedDrivingComponentMatchStick(baseMStick, 0.7, 0.5, true, true, baseMStick.maxAttempts);
            originalAngleMSticks.add(newMStick);
        }

        //DRAW SHAPE VARIATIONS
        int shapeIndex = 0;
        for (DepthLightingPostHocMatchStick originalAngleMStick : originalAngleMSticks) {
            drawer.clear();
            drawer.drawMStick(originalAngleMStick);
            drawer.saveImage(shapeVariationsPath + "/original_angle_with_shape_variation_" + shapeIndex);
            drawer.saveSpec(originalAngleMStick, shapeVariationsPath+"/specs"+"/original_angle_with_shape_variation_" + shapeIndex);
            ThreadUtil.sleep(TIME);
            shapeIndex++;
        }

        //GENERATE FLIPPED VERSIONS
        List<DepthLightingPostHocMatchStick> flippedAngleMSticks = new LinkedList<>();
        for (DepthLightingPostHocMatchStick originalAngleMStick : originalAngleMSticks) {
            DepthLightingPostHocMatchStick flippedStick = new DepthLightingPostHocMatchStick();
            flippedStick.setProperties(12, "SHADE");
            int componentId = 1;
            flippedStick.genFlippedMatchStick(originalAngleMStick, componentId);
            flippedAngleMSticks.add(flippedStick);
        }

        //DRAW FLIPPED VERSIONS
        shapeIndex = 0;
        for (DepthLightingPostHocMatchStick flippedAngleMStick : flippedAngleMSticks) {
            drawer.clear();
            drawer.drawMStick(flippedAngleMStick);
            drawer.saveImage(shapeVariationsPath + "/flipped_angle_with_shape_variation_" + shapeIndex);
            drawer.saveSpec(flippedAngleMStick, shapeVariationsPath+"/specs"+"/flipped_angle_with_shape_variation_" + shapeIndex);
            ThreadUtil.sleep(TIME);
            shapeIndex++;
        }
    }

    @Test
    public void make_figs_for_3_opposite_shape_variations(){
        List<DepthLightingPostHocMatchStick> originalAngleMSticks = new LinkedList<>();
        int numShapeVariations = 2;

        //GENERATE SHAPE VARIATIONS
        String filename = "/home/r2_allen/git/EStimShape/plots/grant_240212/shape_variations/saved/bespoke/original_angle_spec_spec.xml";
        String oppositeShapeVariationsPath = figurePath + "/opposite_shape_variations";
        DepthLightingPostHocMatchStick baseMStick = new DepthLightingPostHocMatchStick();
        baseMStick.setProperties(12, "SHADE");
        baseMStick.genMatchStickFromFile(filename);
        originalAngleMSticks.add(baseMStick);

        for (int i=0; i<numShapeVariations; i++) {
            DepthLightingPostHocMatchStick newMStick = new DepthLightingPostHocMatchStick();
            newMStick.setProperties(12, "SHADE");
            newMStick.genNewComponentMatchStick(baseMStick, 2, 0.75, 0.5, true, newMStick.maxAttempts);
            originalAngleMSticks.add(newMStick);
        }

        //DRAW SHAPE VARIATIONS
        int shapeIndex = 0;
        for (DepthLightingPostHocMatchStick originalAngleMStick : originalAngleMSticks) {
            drawer.clear();
            drawer.drawMStick(originalAngleMStick);
            drawer.saveImage(oppositeShapeVariationsPath + "/original_angle_with_opposite_shape_variation_" + shapeIndex);
            drawer.saveSpec(originalAngleMStick, oppositeShapeVariationsPath+"/specs"+"/original_angle_with_opposite_shape_variation_" + shapeIndex);
            ThreadUtil.sleep(TIME);
            shapeIndex++;
        }

        //GENERATE FLIPPED VERSIONS
        List<DepthLightingPostHocMatchStick> flippedAngleMSticks = new LinkedList<>();
        for (DepthLightingPostHocMatchStick originalAngleMStick : originalAngleMSticks) {
            DepthLightingPostHocMatchStick flippedStick = new DepthLightingPostHocMatchStick();
            flippedStick.setProperties(12, "SHADE");
            int componentId = 1;
            flippedStick.genFlippedMatchStick(originalAngleMStick, componentId);
            flippedAngleMSticks.add(flippedStick);
        }

        //DRAW FLIPPED VERSIONS
        shapeIndex = 0;
        for (DepthLightingPostHocMatchStick flippedAngleMStick : flippedAngleMSticks) {
            drawer.clear();
            drawer.drawMStick(flippedAngleMStick);
            drawer.saveImage(oppositeShapeVariationsPath + "/flipped_angle_with_opposite_shape_variation_" + shapeIndex);
            drawer.saveSpec(flippedAngleMStick, oppositeShapeVariationsPath+"/specs"+"/flipped_angle_with_opposite_shape_variation_" + shapeIndex);
            ThreadUtil.sleep(TIME);
            shapeIndex++;
        }
    }


    @Test
    public void make_noisy_fig(){
        String filepath = "/home/r2_allen/git/EStimShape/plots/grant_240212/noisy";
        String imagePath = "/home/r2_allen/git/EStimShape/plots/grant_240212/shape_variations/saved/bespoke/original_angle.png";
        //GENERATE SHAPE VARIATIONS
        String filename = "/home/r2_allen/git/EStimShape/plots/grant_240212/shape_variations/saved/bespoke/original_angle_spec_spec.xml";
        DepthLightingPostHocMatchStick baseMStick = new DepthLightingPostHocMatchStick();
        baseMStick.setProperties(12, "SHADE");
        baseMStick.genMatchStickFromFile(filename);

        String noiseMapPath = drawer.saveNoiseMap(filepath + "/original_noise_map", baseMStick, 1.0, 1);

        drawer.clear();
        NoisyTranslatableResizableImages noisyImages =
                new NoisyTranslatableResizableImages(
                        60,
                        1,
                        1.0);
        noisyImages.initTextures();
        noisyImages.loadTexture(imagePath, 0);
        noisyImages.loadNoise(noiseMapPath, new Color(255, 255, 255));
        Context context = new Context();
        AbstractRenderer perspectiveRenderer = new PerspectiveRenderer();
        perspectiveRenderer.setDepth(drawer.window.renderer.getDepth());
        perspectiveRenderer.setDistance(drawer.window.renderer.getDistance());
        perspectiveRenderer.setHeight(drawer.window.renderer.getHeight());
        perspectiveRenderer.setWidth(drawer.window.renderer.getWidth());
        perspectiveRenderer.setPupilDistance(drawer.window.renderer.getPupilDistance());
        context.setRenderer(perspectiveRenderer);

        drawer.draw(new Drawable() {
            @Override
            public void draw() {
                noisyImages.draw(true, context, 0, new Coordinates2D(0.0,0.0),
                        new ImageDimensions(11.5, 11.5));
            }
        });

        drawer.saveImage(filepath + "/noisy_original_angle_with_shape_variation_0");

    }

    @Test
    public void make_rand_fig(){
        String filepath = "/home/r2_allen/git/EStimShape/plots/grant_240212/rand/";

        AllenMatchStick randMStick = new AllenMatchStick();

        randMStick.setProperties(12, "SHADE");
        randMStick.genMatchStickRand();

        drawer.clear();
        drawer.drawMStick(randMStick);
        drawer.saveImage(filepath + "rand_shape");

    }

    @Test
    public void make_bespoke_shape(){
        String filename = "/home/r2_allen/git/EStimShape/plots/grant_240212/shape_variations/saved/not_ambiguous/original_angle_with_shape_variation_1_spec.xml";
        DepthLightingPostHocMatchStick baseMStick = new DepthLightingPostHocMatchStick();
        baseMStick.setProperties(12, "SHADE");
        baseMStick.genMatchStickFromFile(filename);

        DepthLightingPostHocMatchStick newMStick = new DepthLightingPostHocMatchStick();
        newMStick.setProperties(12, "SHADE");
        Map<Integer, ComponentMorphParameters> morphParameters = new LinkedHashMap<>();
        morphParameters.put(1, new ComponentMorphParameters(){

            @Override
            public Vector3d morphOrientation(Vector3d oldOrientation) {
                return oldOrientation;
            }

            @Override
            public Double morphRotation(Double oldRotation) {
                return oldRotation;
            }

            @Override
            public Double morphCurvature(Double oldCurvature, AllenMAxisArc arcToMorph) {
                return oldCurvature;
            }

            @Override
            public Double morphLength(Double oldLength) {
                return oldLength;
            }

            @Override
            public RadiusProfile morphRadius(RadiusProfile oldRadiusProfile) {
                RadiusProfile newRadiusProfile = new RadiusProfile(oldRadiusProfile);
                System.out.println("oldradiusProfile.radiusInfo: " + oldRadiusProfile.getInfoForRadius());
                Double oldRadius;
                for (Map.Entry<Integer, RadiusInfo> entry : oldRadiusProfile.getInfoForRadius().entrySet()) {
                    Integer k = entry.getKey();
                    RadiusInfo v = entry.getValue();
                    if (k != 1) {
                        oldRadius = v.getRadius();
                        newRadiusProfile.getRadiusInfo(k).setRadius(oldRadius*0.5);
                    }

                }
                return newRadiusProfile;
            }

            @Override
            public void distribute() {

            }
        });
        newMStick.genMorphedComponentsMatchStick(morphParameters, baseMStick, true);

        drawer.clear();
        drawer.drawMStick(newMStick);
        drawer.saveImage("/home/r2_allen/git/EStimShape/plots/grant_240212/shape_variations/saved/bespoke/original_angle");
        drawer.saveSpec(newMStick, "/home/r2_allen/git/EStimShape/plots/grant_240212/shape_variations/saved/bespoke/original_angle_spec");

        //Flipped Angle
        DepthLightingPostHocMatchStick flippedStick = new DepthLightingPostHocMatchStick();
        flippedStick.setProperties(12, "SHADE");

        flippedStick.genFlippedMatchStick(newMStick, 1);
        drawer.clear();
        drawer.drawMStick(flippedStick);
        drawer.saveImage("/home/r2_allen/git/EStimShape/plots/grant_240212/shape_variations/saved/bespoke/flipped_angle");
        drawer.saveSpec(flippedStick, "/home/r2_allen/git/EStimShape/plots/grant_240212/shape_variations/saved/bespoke/flipped_angle_spec");
    }

    @Test
    public void testCurvature(){
        String filename = "/home/r2_allen/git/EStimShape/plots/grant_240212/shape_variations/saved/weird_curvy/original_angle_with_shape_variation_2_spec.xml";
        DepthLightingPostHocMatchStick baseMStick = new DepthLightingPostHocMatchStick();
        baseMStick.setProperties(12, "SHADE");
        baseMStick.setTextureType("2D");
        baseMStick.genMatchStickFromFile(filename);

        DepthLightingPostHocMatchStick flippedMStick = new DepthLightingPostHocMatchStick();
        flippedMStick.setProperties(12, "SHADE");
        flippedMStick.setTextureType("2D");
        flippedMStick.genFlippedMatchStick(baseMStick, 1);

        drawer.clear();
        drawer.drawMStick(baseMStick);
        ThreadUtil.sleep(TIME);
        drawer.clear();
        drawer.drawMStick(flippedMStick);
        ThreadUtil.sleep(TIME);
    }
}