package org.xper.allen.drawing.composition.noisy;

import org.junit.Before;
import org.junit.Test;
import org.lwjgl.opengl.GL11;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.ga.TestMatchStickDrawer;
import org.xper.drawing.RGBColor;
import org.xper.util.ThreadUtil;

import javax.vecmath.Point3d;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Visual debugging harness for {@link GaussianNoiseMapper}'s noise-circle placement.
 *
 * Modeled after GAMatchStickTest / ProceduralMatchStickTest#drawHullAndNoiseCircle, but instead of
 * asserting anything it turns on {@link GaussianNoiseMapper#setDebugMode(boolean)} so that:
 *   1. the in/out noise checks DO NOT throw (we can see broken placements), and
 *   2. the intermediate quantities used to place the circle are captured and drawn.
 *
 * The whole point is to see the coordinate-system relationship that makes the
 *     {@code shiftAmount = junc.getRad() * scaleForMAxisShape}
 * line behave unexpectedly. Everything is drawn in raw vect_info world space (zoomed so it is
 * visible). Note the two key actors live in DIFFERENT frames at noise time:
 *   - component vect_info is already scaled by scaleForMAxisShape (GAMatchStick.postProcess), but
 *   - junc.getPos() / junc.getRad() are still raw (modifyJuncPtFinalInfoForAnalysis has not run).
 *
 * So we draw the junction position in BOTH frames (raw = magenta, scaled = orange) to make the
 * mismatch obvious.
 */
public class GaussianNoiseMapperDebugTest {

    private TestMatchStickDrawer drawer;
    private GaussianNoiseMapper noiseMapper;

    // Colors for the overlay.
    private static final RGBColor RED = new RGBColor(1, 0, 0);        // in-noise component points
    private static final RGBColor GRAY = new RGBColor(0.4f, 0.4f, 0.4f); // other component points
    private static final RGBColor MAGENTA = new RGBColor(1, 0, 1);    // junction pos (RAW, as the math uses it)
    private static final RGBColor ORANGE = new RGBColor(1, 0.55f, 0); // junction pos (SCALED, where it visually is)
    private static final RGBColor YELLOW = new RGBColor(1, 1, 0);     // starting position (after inward shift)
    private static final RGBColor GREEN = new RGBColor(0, 1, 0);      // noise origin (circle center)
    private static final RGBColor CYAN = new RGBColor(0, 1, 1);       // noise circle

    @Before
    public void setUp() {
        drawer = new TestMatchStickDrawer();
        drawer.setup(500, 500);

        noiseMapper = new GaussianNoiseMapper();
        noiseMapper.setWidth(500);
        noiseMapper.setHeight(500);
        noiseMapper.setBackground(0);
        noiseMapper.setDoEnforceHiddenJunction(true);
        // The whole reason this test exists: don't throw, just capture & draw.
        noiseMapper.setDebugMode(true);
    }

    @Test
    public void visualize_noise_circle_placement() {
        int size = 4; // -> scaleForMAxisShape

        // 1. A base shape, then a shape grown from one of its components so we get a special
        //    (driving) component that should be hidden in noise, with a junction connecting it.
        ProceduralMatchStick base = new ProceduralMatchStick(noiseMapper);
        base.setProperties(size, "SHADE", 1.0);
        base.genMatchStickRand();
        base.setMaxAttempts(-1);

        ProceduralMatchStick sample = null;
        while (sample == null) {
            try {
                ProceduralMatchStick candidate = new ProceduralMatchStick(noiseMapper);
                candidate.PARAM_nCompDist = new double[]{0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0};
                candidate.setProperties(size, "SHADE", 1.0);
                candidate.genMatchStickFromComponent(base, Collections.singletonList(1), 0, ProceduralMatchStick.maxAttempts);
                sample = candidate;
            } catch (Exception e) {
                System.out.println("regen base/sample: " + e.getMessage());
                base = new ProceduralMatchStick(noiseMapper);
                base.setProperties(size, "SHADE", 1.0);
                base.genMatchStickRand();
                base.setMaxAttempts(-1);
            }
        }

        List<Integer> compsToNoise = sample.getSpecialEndComp();
        System.out.println("special end (in-noise) comps: " + compsToNoise);

        // 2. Pick a noise radius that is comparable to the shape so the circle is actually visible.
        //    (The simple ProceduralMatchStick constructor leaves noiseRadiusMm at its default, which
        //    is unrelated to this shape's scale.) Change this to experiment with coverage.
        double extent = maxExtentOfInNoiseComps(sample, compsToNoise);
        sample.noiseRadiusMm = extent * 0.7;

        // 3. Run the check. debugMode means this won't throw even if points fall outside.
        noiseMapper.checkInNoise(sample, compsToNoise, 0.0);

        // 4. Pull out what the math did.
        //    magenta = junction in raw mAxis space (the OLD anchor); orange = junction mapped into the
        //    scaled vect_info frame (where the junction actually is). After the fix, the noise circle
        //    (cyan) / starting position (yellow) should be anchored on ORANGE, not magenta.
        Point3d juncRaw = noiseMapper.debug_junctionPosition;
        Point3d juncScaled = noiseMapper.debug_junctionPositionScaled;
        Point3d startPos = noiseMapper.debug_startingPosition;
        Point3d noiseOrigin = noiseMapper.debug_noiseOrigin3d;

        System.out.println("==== NOISE PLACEMENT DEBUG ====");
        System.out.println("scaleForMAxisShape:        " + sample.getScaleForMAxisShape());
        System.out.println("junction pos (RAW/magenta):    " + juncRaw);
        System.out.println("junction pos (SCALED/orange):  " + juncScaled);
        System.out.println("junction radius (RAW):     " + noiseMapper.debug_junctionRadius);
        System.out.println("junction radius * scale:   " + (noiseMapper.debug_junctionRadius * sample.getScaleForMAxisShape()));
        System.out.println("shiftAmount (rad*scale):   " + noiseMapper.debug_shiftAmount);
        System.out.println("projected tangent:         " + noiseMapper.debug_projectedTangent);
        System.out.println("starting position:         " + startPos);
        System.out.println("noise origin:              " + noiseOrigin);
        System.out.println("noise radius:              " + noiseMapper.debug_noiseRadiusMm);
        System.out.println("in-noise comp extent:      " + extent);
        System.out.println("===============================");

        // 5. Draw it all in one frame, zoomed so the small raw coordinates are visible.
        final double zoom = 50.0 / Math.max(extent, 1e-6);
        final ProceduralMatchStick mStick = sample;
        final List<Integer> inNoise = compsToNoise;

        drawer.draw(new Drawable() {
            @Override
            public void draw() {
                GL11.glDisable(GL11.GL_DEPTH_TEST);
                GL11.glPushMatrix();
                GL11.glScalef((float) zoom, (float) zoom, 1f);

                // Component point clouds.
                for (int compId : mStick.getCompIds()) {
                    if (compId == 0) continue;
                    RGBColor c = inNoise.contains(compId) ? RED : GRAY;
                    drawPoints(mStick.getComp()[compId].getVect_info(), c, 2f);
                }

                // Junction position in both frames + its radius circles.
                if (juncRaw != null) {
                    drawPoint(juncRaw, MAGENTA, 8f);
                    drawCircleXY(juncRaw, noiseMapper.debug_junctionRadius, MAGENTA);          // raw radius
                    drawPoint(juncScaled, ORANGE, 8f);
                    drawCircleXY(juncScaled, noiseMapper.debug_junctionRadius * mStick.getScaleForMAxisShape(), ORANGE); // scaled radius
                }

                // Starting position (junction shifted inward by shiftAmount) and the shift line.
                if (startPos != null && juncRaw != null) {
                    drawPoint(startPos, YELLOW, 8f);
                    drawLine(juncRaw, startPos, YELLOW);
                }

                // The noise circle itself.
                if (noiseOrigin != null) {
                    drawPoint(noiseOrigin, GREEN, 8f);
                    drawCircleXY(noiseOrigin, noiseMapper.debug_noiseRadiusMm, CYAN);
                }

                GL11.glPopMatrix();
            }
        });

        drawer.saveImage("/tmp/noise_debug");
        ThreadUtil.sleep(60000);
    }

    private double maxExtentOfInNoiseComps(ProceduralMatchStick mStick, List<Integer> compsToNoise) {
        double max = 0;
        List<Integer> comps = compsToNoise.isEmpty() ? new ArrayList<>(mStick.getCompIds()) : compsToNoise;
        for (int compId : comps) {
            if (compId == 0) continue;
            for (Point3d p : mStick.getComp()[compId].getVect_info()) {
                if (p != null) {
                    max = Math.max(max, Math.hypot(p.x, p.y));
                }
            }
        }
        return max;
    }

    // ---- tiny GL helpers (assume the caller already set color-mode / pushed matrix) ----

    private static void drawPoints(Point3d[] points, RGBColor color, float pointSize) {
        GL11.glPointSize(pointSize);
        GL11.glColor3f(color.getRed(), color.getGreen(), color.getBlue());
        GL11.glBegin(GL11.GL_POINTS);
        for (Point3d p : points) {
            if (p != null) {
                GL11.glVertex3d(p.x, p.y, p.z);
            }
        }
        GL11.glEnd();
    }

    private static void drawPoint(Point3d p, RGBColor color, float pointSize) {
        GL11.glPointSize(pointSize);
        GL11.glColor3f(color.getRed(), color.getGreen(), color.getBlue());
        GL11.glBegin(GL11.GL_POINTS);
        GL11.glVertex3d(p.x, p.y, p.z);
        GL11.glEnd();
    }

    private static void drawLine(Point3d a, Point3d b, RGBColor color) {
        GL11.glLineWidth(2f);
        GL11.glColor3f(color.getRed(), color.getGreen(), color.getBlue());
        GL11.glBegin(GL11.GL_LINES);
        GL11.glVertex3d(a.x, a.y, a.z);
        GL11.glVertex3d(b.x, b.y, b.z);
        GL11.glEnd();
    }

    private static void drawCircleXY(Point3d center, double radius, RGBColor color) {
        GL11.glLineWidth(2f);
        GL11.glColor3f(color.getRed(), color.getGreen(), color.getBlue());
        GL11.glBegin(GL11.GL_LINE_LOOP);
        int segments = 120;
        for (int i = 0; i < segments; i++) {
            double theta = 2.0 * Math.PI * i / segments;
            GL11.glVertex3d(center.x + radius * Math.cos(theta), center.y + radius * Math.sin(theta), center.z);
        }
        GL11.glEnd();
    }
}
