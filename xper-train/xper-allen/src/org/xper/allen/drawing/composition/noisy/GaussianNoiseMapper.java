package org.xper.allen.drawing.composition.noisy;

import org.xper.Dependency;
import org.xper.alden.drawing.renderer.AbstractRenderer;
import org.xper.allen.drawing.composition.AllenTubeComp;
import org.xper.allen.drawing.composition.experiment.NoiseException;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.stick.JuncPt_struct;

import javax.imageio.ImageIO;
import javax.vecmath.Point2d;
import javax.vecmath.Point3d;
import javax.vecmath.Vector2d;
import javax.vecmath.Vector3d;
import java.awt.Color;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.util.*;
import java.util.function.IntPredicate;

public class GaussianNoiseMapper implements NAFCNoiseMapper {
    @Dependency
    public int width;
    @Dependency
    public int height;
    @Dependency
    private double background;
    @Dependency
    /**
     * If true, the noise circle will chosen so that the junction of the in-noise components is completely hidden.
     * If false, the noise circle will be chosen so that 75% of the points in the in-noise components are inside the noise circle.
     *
     * When the junction is fully hidden, because of the gaussian fade, the noise circle will be larger than the junction, which
     * can obscure more of the shape than wanted.
     *
     */
    private boolean doEnforceHiddenJunction = true;

    /*
    08/19/24 AC: These debugging variables were used to visualize the noise circle and the points that were used to check
    whether or not points inside set mutated mSticks were within the noise circle.
     */
    public List<Point2d> debug_points_outside = new LinkedList<>();
    public List<Point2d> debug_points_vect = new LinkedList<>();
    public List<Point2d> debug_points_obj1 = new LinkedList<>();
    public Point2d debug_noise_origin;

    /**
     * 06/23/26 AC: When true, the noise mapper runs in a non-throwing "debug" mode so that the
     * placement of the noise circle can be visualized even when the in/out checks would normally
     * fail. The checks still run and print their results, but {@link NoiseException}s are suppressed.
     *
     * In addition, the intermediate quantities used to place the noise circle (junction position,
     * junction radius, the inward shift, the starting position, the noise origin and the noise
     * radius) are captured in the debug_* fields below so a test can draw them. This lets us inspect
     * the coordinate-system relationship between junc.getPos()/junc.getRad() (raw mAxis space, since
     * modifyJuncPtFinalInfoForAnalysis has not run yet at noise time) and the component vect_info
     * (already scaled by scaleForMAxisShape in GAMatchStick.postProcess).
     *
     * Defaults to false so production behavior is unchanged.
     */
    private boolean debugMode = false;

    // Captured during the most recent noise-origin computation when debugMode is true.
    public Point3d debug_junctionPosition;       // junc.getPos() in raw mAxis space (NOT where the junction visually is)
    public Point3d debug_junctionPositionScaled; // junc.getPos() mapped into the scaled vect_info frame (where the junction actually is)
    public double debug_junctionRadius;      // junc.getRad() as used by the noise math (raw)
    public double debug_scaleForMAxisShape;  // scale factor multiplied into the shift
    public double debug_shiftAmount;         // inward shift applied to junc.getPos()
    public Point3d debug_startingPosition;   // junc.getPos() shifted inward by debug_shiftAmount
    public Vector3d debug_projectedTangent;  // tangent the noise origin is projected along
    public Point3d debug_noiseOrigin3d;      // computed center of the noise circle
    public double debug_noiseRadiusMm;       // radius of the noise circle

    /**
     * Minimum fraction of the to-hide component's points that must fall inside the noise circle for
     * checkInNoise to pass. Defaults to the historical 0.95; set to 1.0 to require the whole limb.
     */
    private double percentRequiredInside = 0.95;

    /**
     * When true, calculateNoiseOrigin replaces the fixed geometric shift (junc.getRad()*scale) with a
     * search for the SMALLEST shift along the aim direction that gets percentRequiredInsideForSearch of
     * the to-hide component inside the (fixed-radius) circle. Smallest shift also maximizes how much of
     * the rest stays outside, so the two goals are aligned. Defaults to false (current behavior).
     */
    private boolean optimizeShiftToHideComps = false;
    /** Target inside-fraction the shift search aims to reach (1.0 = hide the whole limb). */
    private double targetInsideFraction = 1.0;
    /** Number of discrete shift samples the search scans between origin-at-junction and full radius. */
    private int shiftSearchSteps = 200;


    @Override
    public String mapNoise(ProceduralMatchStick mStick,
                           double amplitude,
                           List<Integer> specialCompIndcs,
                           AbstractRenderer renderer,
                           String path) {
        File ouptutFile = new File(path);
        BufferedImage img = generateGaussianNoiseMapFor(mStick, width, height, amplitude, background, renderer, specialCompIndcs);
        try {
            ImageIO.write(img, "png", ouptutFile);
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
        return ouptutFile.getAbsolutePath();
    }

    @Override
    public void checkInNoise(ProceduralMatchStick proceduralMatchStick, List<Integer> mustBeInNoiseCompIds, double percentRequiredOutsideNoise) throws NoiseException{
        Point3d noiseOrigin = calculateNoiseOrigin(proceduralMatchStick, mustBeInNoiseCompIds);
        proceduralMatchStick.setNoiseOrigin(noiseOrigin);
        double radius = proceduralMatchStick.noiseRadiusMm;
        debug_noise_origin = new Point2d(noiseOrigin.getX(), noiseOrigin.getY());
        if (debugMode) {
            debug_noiseOrigin3d = new Point3d(noiseOrigin);
            debug_noiseRadiusMm = radius;
            captureDebugPoints(proceduralMatchStick, mustBeInNoiseCompIds, noiseOrigin, radius);
        }

        double actualPercentageInside = fractionInside(proceduralMatchStick, mustBeInNoiseCompIds, noiseOrigin, radius);
        if (actualPercentageInside < percentRequiredInside){
            String msg = "Found points outside of noise circle: " + actualPercentageInside + " inside, with noise Radius: " + radius;
            if (debugMode) {
                System.out.println("[NOISE DEBUG] (suppressed) " + msg);
            } else {
                throw new NoiseException(msg);
            }
        }
        System.out.println("PERCENT REQUIRED INSIDE: " + percentRequiredInside);
        System.out.println("ACTUAL PERCENT INSIDE: " + actualPercentageInside);

        double percentOutside = fractionOutside(proceduralMatchStick, mustBeInNoiseCompIds, noiseOrigin, radius);
        System.out.println("%%%% OUTSIDE: " + percentOutside);
        if (percentOutside < percentRequiredOutsideNoise){
            if (debugMode) {
                System.out.println("[NOISE DEBUG] (suppressed) Not enough points outside of noise circle: " + percentOutside);
            } else {
                throw new NoiseException("Not enough points outside of noise circle");
            }
        }
        System.out.println("SUCCEEDED CHECK IN NOISE");
    }

    /**
     * Fraction of the given components' vect_info points that lie inside the circle. Pure (no side
     * effects), so both checkInNoise and the shift search can call it to agree on coverage.
     */
    public double fractionInside(ProceduralMatchStick mStick, List<Integer> comps, Point3d origin, double radius) {
        Point2d center = new Point2d(origin.getX(), origin.getY());
        int total = 0, inside = 0;
        for (int compId : comps) {
            for (Point3d p : mStick.getComp()[compId].getVect_info()) {
                if (p != null) {
                    total++;
                    if (isPointWithinCircle(new Point2d(p.getX(), p.getY()), center, radius)) {
                        inside++;
                    }
                }
            }
        }
        return total == 0 ? 1.0 : (double) inside / total;
    }

    /**
     * Fraction of the points belonging to components NOT in inNoiseComps that lie outside the circle.
     */
    public double fractionOutside(ProceduralMatchStick mStick, List<Integer> inNoiseComps, Point3d origin, double radius) {
        Point2d center = new Point2d(origin.getX(), origin.getY());
        int total = 0, outside = 0;
        for (int compId = 1; compId <= mStick.getnComponent(); compId++) {
            if (inNoiseComps.contains(compId)) {
                continue;
            }
            for (Point3d p : mStick.getComp()[compId].getVect_info()) {
                if (p != null) {
                    total++;
                    if (!isPointWithinCircle(new Point2d(p.getX(), p.getY()), center, radius)) {
                        outside++;
                    }
                }
            }
        }
        return total == 0 ? 1.0 : (double) outside / total;
    }

    private void captureDebugPoints(ProceduralMatchStick mStick, List<Integer> inNoiseComps, Point3d origin, double radius) {
        debug_points_vect.clear();
        debug_points_obj1.clear();
        debug_points_outside.clear();
        Point2d center = new Point2d(origin.getX(), origin.getY());
        for (int compId : inNoiseComps) {
            for (Point3d p : mStick.getComp()[compId].getVect_info()) {
                if (p != null) {
                    Point2d p2 = new Point2d(p.getX(), p.getY());
                    debug_points_vect.add(p2);
                    if (!isPointWithinCircle(p2, center, radius)) {
                        debug_points_outside.add(p2);
                    }
                }
            }
        }
    }

    public Point3d calculateNoiseOrigin(ProceduralMatchStick proceduralMatchStick, List<Integer> compsToBeInNoise){
        Point3d point3d = new Point3d();

        if (compsToBeInNoise.size() == 1){

            int specialCompId = compsToBeInNoise.get(0);

            for (JuncPt_struct junc : proceduralMatchStick.getJuncPt()) {
                if (junc != null) {
                    int finalSpecialCompId = specialCompId;
                    int numCompsInJuncThatMatchSpecialId = Arrays.stream(junc.getCompIds()).filter(new IntPredicate() {
                        @Override
                        public boolean test(int x) {
                            return x == finalSpecialCompId;
                        }
                    }).toArray().length;
                    boolean isContainsSpecialId = numCompsInJuncThatMatchSpecialId == 1;
                    if (isContainsSpecialId) {
                        if (junc.getnComp() == 2) {
                            int baseCompId = ProceduralMatchStick.findBaseCompId(specialCompId, junc);
                            return calcProjectionFromSingleJunctionWithSingleComp(proceduralMatchStick, baseCompId, junc, compsToBeInNoise);
                        } else if (junc.getnComp() > 2) {
                            return calcProjectionFromJunctionWithMultiComp(proceduralMatchStick, specialCompId, junc, compsToBeInNoise);
                        } else{
                            throw new IllegalArgumentException("Junction has less than 2 components");
                        }
                    }
                }
            }
        } else if (compsToBeInNoise.size() == 2){
            int baseCompId = -1;

            for (JuncPt_struct junc : proceduralMatchStick.getJuncPt()) {
                if (junc!= null){
                    for (int toNoiseCompId : compsToBeInNoise){
                        int potentialBaseComp = ProceduralMatchStick.findBaseCompId(toNoiseCompId, junc);
                        if (!compsToBeInNoise.contains(potentialBaseComp)){
                            baseCompId = potentialBaseComp;
                        }
                    }
                }
            }


            for (JuncPt_struct junc : proceduralMatchStick.getJuncPt()) {
                if (junc != null) {

                    int finalBaseCompId = baseCompId;
                    int numMatch = Arrays.stream(junc.getCompIds()).filter(new IntPredicate() {
                        @Override
                        public boolean test(int x) {
                            return x == finalBaseCompId;
                        }
                    }).toArray().length;

                    if (numMatch == 1) {
                        return calcProjectionFromSingleJunctionWithSingleComp(proceduralMatchStick, baseCompId, junc, compsToBeInNoise);
                    }
                }
            }

        } else{
            throw new IllegalArgumentException("num Comps to be in noise must be 1 or 2. More than 2 not implemented yet");
        }


        return point3d;
    }



    protected static boolean isPointWithinCircle(Point2d point, Point2d center, double radius) {
        return point.distance(center) <= radius;
    }

    /**
     * Bases projection based on the base comp.
     * @param proceduralMatchStick
     * @param baseCompId
     * @param junc
     * @return
     */
    public Point3d calcProjectionFromSingleJunctionWithSingleComp(ProceduralMatchStick proceduralMatchStick, Integer baseCompId, JuncPt_struct junc, List<Integer> toHideComps) {
        // Find tangent to project along for noise origin
        proceduralMatchStick.projectedTangent = getJuncTangentForSingle(proceduralMatchStick, junc, baseCompId);
        proceduralMatchStick.projectedTangent = new Vector3d(proceduralMatchStick.projectedTangent.x, proceduralMatchStick.projectedTangent.y, 0);

        return placeNoiseOrigin(proceduralMatchStick, junc, proceduralMatchStick.projectedTangent, toHideComps);
    }

    public static Vector3d getJuncTangentForSingle(ProceduralMatchStick proceduralMatchStick, JuncPt_struct junc, int baseCompId) {
        Vector3d tangent = junc.getTangentOfOwner(baseCompId);
        Vector3d reversedTangent = new Vector3d(tangent);
        reversedTangent.negate();
        ArrayList<Vector3d> possibleTangents = new ArrayList<>(2);
        possibleTangents.add(tangent);
        possibleTangents.add(reversedTangent);
        tangent = getVectorPointingFurthestAwayFromPoint(possibleTangents, junc.getPos(), proceduralMatchStick.getComp()[baseCompId].getmAxisInfo().getmPts()[26]);
        return tangent;
    }

    /**
     * Finds the vector from a list that points furthest away from a given point, considering a starting point for each vector.
     *
     * @param vectors     The list of vectors.
     * @param startPoint  The starting point from which each vector originates.
     * @param target      The target point.
     * @return The vector that points furthest away from the target point.
     */
    private static Vector3d getVectorPointingFurthestAwayFromPoint(List<Vector3d> vectors, Point3d startPoint, Point3d target) {
        Vector3d directionToTarget = new Vector3d();
        directionToTarget.sub(target, new Vector3d(startPoint.x, startPoint.y, startPoint.z)); // Direction from start point to target

        double minDotProduct = Double.MAX_VALUE;
        Vector3d mostOppositeVector = null;

        for (Vector3d vec : vectors) {
            Vector3d normalizedVec = new Vector3d(vec);
            normalizedVec.normalize();

            Vector3d normalizedDirectionToTarget = new Vector3d(directionToTarget);
            normalizedDirectionToTarget.normalize();

            double dotProduct = normalizedVec.dot(normalizedDirectionToTarget);
            if (dotProduct < minDotProduct) {
                minDotProduct = dotProduct;
                mostOppositeVector = vec;
            }
        }

        return mostOppositeVector;
    }

    public static Vector3d getJuncTangentForMulti(ProceduralMatchStick proceduralMatchStick, JuncPt_struct junc, int tangentOwnerCompId) {
        Vector3d tangent = junc.getTangentOfOwner(tangentOwnerCompId);
        Vector3d reversedTangent = new Vector3d(tangent);
        reversedTangent.negate();
        ArrayList<Vector3d> possibleTangents = new ArrayList<>(2);
        possibleTangents.add(tangent);
        possibleTangents.add(reversedTangent);
        tangent = getVectorPointingAtPoint(possibleTangents, junc.getPos(), proceduralMatchStick.getComp()[tangentOwnerCompId].getmAxisInfo().getmPts()[26]);
        return tangent;
    }

    /**
     * Finds the vector from a list that points most directly at a given point from a specific starting point.
     *
     * @param vectors   The list of vectors.
     * @param startPoint The starting point from which the vectors originate.
     * @param target    The target point.
     * @return The vector that points most directly at the target point from the starting point.
     */
    public static Vector3d getVectorPointingAtPoint(List<Vector3d> vectors, Point3d startPoint, Point3d target) {
        Vector3d directionToTarget = new Vector3d(target.x - startPoint.x, target.y - startPoint.y, target.z - startPoint.z);

        double maxDotProduct = -Double.MAX_VALUE;
        Vector3d mostDirectVector = null;

        for (Vector3d vec : vectors) {
            // Here, assume that vectors are already originating from the startPoint,
            // if not, you need to translate them by subtracting startPoint from their origin.
            Vector3d normalizedVec = new Vector3d(vec);
            normalizedVec.normalize();

            double dotProduct = normalizedVec.dot(directionToTarget);
            if (dotProduct > maxDotProduct) {
                maxDotProduct = dotProduct;
                mostDirectVector = vec;
            }
        }

        return mostDirectVector;
    }

    /**
     * Computes a point along the 3D tangent from a given 3D point, with z set to 0.
     *
     * @param startPoint The starting 3D point.
     * @param tangent    The 3D tangent vector (not required to be normalized).
     * @param distance   The distance to move along the tangent.
     * @return A new 3D point along the tangent with z set to 0.
     */
    public static Point3d pointAlong2dTangent(Point3d startPoint, Vector3d tangent, double distance) {
        Vector2d projectedTangent = projectTo2D(tangent);
        Point2d start2d = new Point2d(startPoint.x, startPoint.y);
        Point2d result2d = point2dAlongTangent(start2d, projectedTangent, distance);
        return new Point3d(result2d.x, result2d.y, 0);
    }

    /**
     * Bases projection based off of the members of the junction that are NOT the specialComp
     * @param proceduralMatchStick
     * @param specialCompId
     * @param junc
     * @return
     */
    public Point3d calcProjectionFromJunctionWithMultiComp(ProceduralMatchStick proceduralMatchStick, Integer specialCompId, JuncPt_struct junc, List<Integer> toHideComps) {
        // Collect tangents for this junction - excluding special component
        List<Vector3d> nonSpecialTangents = new LinkedList<>();
        List<Integer> jIndicesForTangent = new LinkedList<>();
        int[] connectedCompIds = junc.getCompIds();
        for (int connectedCompId : connectedCompIds){
            if (connectedCompId != 0 && connectedCompId != specialCompId) {
                Vector3d tangent = getJuncTangentForMulti(proceduralMatchStick, junc, connectedCompId);
                nonSpecialTangents.add(tangent);
                jIndicesForTangent.add(junc.getJIndexOfComp(connectedCompId));
            }
        }

        // For every unique pair of tangents, find the external angle
        Map<List<Vector3d>, Double> externalAnglesForTangentPairs = new HashMap<>();
        Map<List<Vector3d>, List<Integer>> jIndicesForTangentPairs = new HashMap<>();
        for (int i = 0; i < nonSpecialTangents.size(); i++){
            for (int j = i + 1; j < nonSpecialTangents.size(); j++){
                Vector3d tangent1 = nonSpecialTangents.get(i);
                Vector3d tangent2 = nonSpecialTangents.get(j);
                // The noise origin is placed in the image (XY) plane and the bisector below is computed
                // in 2D, so choose the widest gap using the 2D-projected angle, not the 3D angle. Two
                // tangents far apart in 3D can project to nearly-collinear 2D vectors (and vice versa);
                // using the 3D angle here can select a pair whose 2D bisector does not match the gap we
                // actually see in the image.
                double externalAngle = 2*Math.PI - projectTo2D(tangent1).angle(projectTo2D(tangent2));
                externalAnglesForTangentPairs.put(Arrays.asList(tangent1, tangent2), externalAngle);
                int jIndex1 = jIndicesForTangent.get(i);
                int jIndex2 = jIndicesForTangent.get(j);
                jIndicesForTangentPairs.put(Arrays.asList(tangent1, tangent2), Arrays.asList(jIndex1, jIndex2));
            }
        }

        // Get the pair with the smallest external angle
        List<Vector3d> tangentPairWithSmallestExternalAngle = Collections.min(externalAnglesForTangentPairs.entrySet(), Comparator.comparingDouble(Map.Entry::getValue)).getKey();

        // Calculate bisector of smallest external angle
        Vector2d bisector = new Vector2d();
        Vector2d tangent1 = new Vector2d(tangentPairWithSmallestExternalAngle.get(0).x, tangentPairWithSmallestExternalAngle.get(0).y);
        Vector2d tangent2 = new Vector2d(tangentPairWithSmallestExternalAngle.get(1).x, tangentPairWithSmallestExternalAngle.get(1).y);
        tangent1.normalize();
        tangent2.normalize();
        bisector.add(tangent1);
        bisector.add(tangent2);
        bisector.normalize();

        // Orient the bisector toward the special component (the one we are hiding) instead of blindly
        // negating. The non-special tangents point toward their component bodies, so the un-flipped
        // bisector points between/toward the non-special comps; we want to aim into the gap where the
        // special comp sits. An unconditional negate assumes the special comp is on the reflex side of
        // the two non-special comps, which is wrong when the special comp lies in the smaller arc
        // between them (then the offset goes the wrong way). Use the special comp's own junction
        // tangent as ground truth and flip the bisector so it points into the same half-plane.
        Vector2d specialDir = projectTo2D(getJuncTangentForMulti(proceduralMatchStick, junc, specialCompId));
        if (bisector.dot(specialDir) < 0) {
            bisector.negate();
        }
        Vector3d bisector_3d = new Vector3d(bisector.getX(), bisector.getY(), 0);
        proceduralMatchStick.projectedTangent = bisector_3d;

        return placeNoiseOrigin(proceduralMatchStick, junc, bisector_3d, toHideComps);
    }

    /**
     * Turns an aim direction into a noise-circle origin. Default behavior is the fixed geometric shift
     * (chooseStartingPoint + project by noiseRadius). When optimizeShiftToHideComps is on, it instead
     * searches for the smallest shift along the aim direction that hides the to-hide component.
     */
    private Point3d placeNoiseOrigin(ProceduralMatchStick mStick, JuncPt_struct junc, Vector3d aimTangent, List<Integer> toHideComps) {
        if (optimizeShiftToHideComps) {
            return searchSmallestShiftOrigin(mStick, junc, aimTangent, toHideComps);
        }
        Point3d startingPosition = chooseStartingPoint(mStick, junc, aimTangent, mStick.getScaleForMAxisShape());
        System.out.println("Starting position: " + startingPosition);
        return pointAlong2dTangent(startingPosition, aimTangent, mStick.noiseRadiusMm);
    }

    /**
     * Scans the noise-circle center along the (fixed) aim direction and returns the SMALLEST shift that
     * gets targetInsideFraction of the to-hide component inside the fixed-radius circle.
     *
     * The center is a linear function of the inward shift s:
     *     origin(s) = scaledJunc + D * (radius - s)
     * where D is the unit aim direction and scaledJunc is the junction in the vect_info frame. s = 0
     * puts the junction on the circle's near edge (half the limb out); growing s pulls the circle back
     * over the limb. Smallest qualifying s also keeps the circle pushed maximally away from the rest of
     * the shape, so it maximizes how much stays outside. If nothing in [0, radius] qualifies, the limb
     * cannot be hidden by this radius; we return the center-on-junction circle and let checkInNoise
     * reject it.
     */
    private Point3d searchSmallestShiftOrigin(ProceduralMatchStick mStick, JuncPt_struct junc, Vector3d aimTangent, List<Integer> toHideComps) {
        Point3d scaledJunc = mStick.transCorScalePoint(junc.getPos());
        Vector2d d = projectTo2D(aimTangent);
        d.normalize();
        double radius = mStick.noiseRadiusMm;
        double step = radius / shiftSearchSteps;

        Point3d chosen = new Point3d(scaledJunc.x, scaledJunc.y, 0); // fallback: centered on junction (max coverage)
        for (double s = 0; s <= radius + 1e-9; s += step) {
            double offset = radius - s;
            Point3d origin = new Point3d(scaledJunc.x + d.x * offset, scaledJunc.y + d.y * offset, 0);
            if (fractionInside(mStick, toHideComps, origin, radius) >= targetInsideFraction) {
                chosen = origin;
                break;
            }
        }

        if (debugMode) {
            debug_junctionPosition = new Point3d(junc.getPos());
            debug_junctionPositionScaled = new Point3d(scaledJunc);
            debug_junctionRadius = junc.getRad();
            debug_scaleForMAxisShape = mStick.getScaleForMAxisShape();
            debug_projectedTangent = new Vector3d(aimTangent);
            // near edge of the circle (toward the rest of the shape) = origin - D*radius
            debug_startingPosition = new Point3d(chosen.x - d.x * radius, chosen.y - d.y * radius, 0);
            debug_shiftAmount = radius - (new Vector2d(chosen.x - scaledJunc.x, chosen.y - scaledJunc.y)).dot(d);
        }
        return chosen;
    }

    public Point3d chooseStartingPoint(ProceduralMatchStick mStick, JuncPt_struct junc, Vector3d tangent, double scaleForMAxisShape) {
        // junc.getPos() is still in raw mAxis space at noise time (modifyJuncPtFinalInfoForAnalysis
        // has not run yet), but the component vect_info we anchor/test against has already been scaled
        // by scaleForMAxisShape about the mass center (GAMatchStick.postProcess). Put the junction into
        // that same scaled frame so the noise circle is anchored where the junction actually is rather
        // than at the (smaller, mass-center-ward) raw position. The mass center is invariant under this
        // scaling, so transCorScalePoint reproduces exactly the transform applied to vect_info.
        Point3d scaledJuncPos = mStick.transCorScalePoint(junc.getPos());

        // The junction radius lives in the same raw frame as junc.getPos(), so it must be scaled too
        // to express the shift in the scaled frame.
        double shiftAmount = doEnforceHiddenJunction ? junc.getRad()*scaleForMAxisShape : 0.0;

        // The noise map lives in the image (XY) plane, and the noise-radius step below
        // (pointAlong2dTangent) measures its distance in 2D. Do the inward shift the same way:
        // project the tangent into 2D and re-normalize (inside point2dAlongTangent) so the shift
        // covers the full shiftAmount in-plane regardless of any z-component. Doing the shift with a
        // 3D-normalized tangent would foreshorten it in the image and not go far enough to clear the
        // junction. Reverse it so we step backwards (into the shape, toward the base component).
        Vector2d reverseTangent2d = projectTo2D(tangent);
        reverseTangent2d.negate(); //reverse so we end up with a point inside of the shape
        Point2d start2d = point2dAlongTangent(
                new Point2d(scaledJuncPos.x, scaledJuncPos.y),
                reverseTangent2d,
                shiftAmount);
        Point3d startingPosition = new Point3d(start2d.x, start2d.y, 0);
        if (debugMode) {
            debug_junctionPosition = new Point3d(junc.getPos());
            debug_junctionPositionScaled = new Point3d(scaledJuncPos);
            debug_junctionRadius = junc.getRad();
            debug_scaleForMAxisShape = scaleForMAxisShape;
            debug_shiftAmount = shiftAmount;
            debug_startingPosition = new Point3d(startingPosition);
            debug_projectedTangent = new Vector3d(tangent);
        }
        return startingPosition;
    }

    protected static Point3d choosePositionAlongTangent(Vector3d tangent, Point3d pos, double distance) {
        Vector3d normalizedTangent = new Vector3d(tangent);
        normalizedTangent.normalize();
        normalizedTangent.scale(distance);
        Point3d startingPosition = new Point3d(pos);
        startingPosition.add(normalizedTangent);
        return startingPosition;

    }

    public BufferedImage generateGaussianNoiseMapFor(ProceduralMatchStick mStick,
                                                            int width, int height,
                                                            double amplitude, double background,
                                                            AbstractRenderer renderer, int specialCompIndx){

        return generateGaussianNoiseMapFor(mStick, width, height, amplitude, background, renderer, Collections.singletonList(specialCompIndx));

    }

    public BufferedImage generateGaussianNoiseMapFor(ProceduralMatchStick mStick,
                                                            int width, int height,
                                                            double amplitude, double background,
                                                            AbstractRenderer renderer, List<Integer> compsToNoise){

        // Prefer a noise origin pre-set on the mStick (e.g. by checkInNoise, or copied from an
        // intact parent whose driving component was later deleted). Falls back to recomputing
        // from this mStick's geometry, which is the only option for shapes that never had
        // checkInNoise run.
        Point3d noiseOrigin = mStick.getNoiseOrigin();
        if (noiseOrigin == null) {
            noiseOrigin = calculateNoiseOrigin(mStick, compsToNoise);
        }


//        double sigmaPixels = mmToPixels(renderer, mStick.noiseRadiusMm/6);
        double sigmaPixels = mmToPixels(renderer, mStick.getRf().getRadius()/48);
//        double sigmaPixels = 0;

        Coordinates2D noiseOriginPixels = convertMmToPixelCoordinates(noiseOrigin, renderer);

        return GaussianNoiseMapper.generateTruncatedGaussianNoiseMap(width, height,
                noiseOriginPixels.getX(), noiseOriginPixels.getY(),
                mmToPixels(renderer, mStick.noiseRadiusMm), amplitude,
                sigmaPixels, sigmaPixels,
                background);

    }

    public static double mmToPixels(AbstractRenderer renderer, double mm) {
        Coordinates2D pixels = renderer.mm2pixel(new Coordinates2D(mm, mm));
        return pixels.getX();

    }
    /**
     * Projects a 3D vector onto 2D by dropping the z-component.
     *
     * @param vector The 3D vector.
     * @return The 2D vector projection.
     */
    public static Vector2d projectTo2D(Vector3d vector) {
        return new Vector2d(vector.x, vector.y);
    }

    /**
     * Computes a point along the 2D tangent from a given 2D point.
     *
     * @param startPoint The starting 2D point.
     * @param tangent    The 2D tangent vector (not required to be normalized).
     * @param distance   The distance to move along the tangent.
     * @return A new 2D point along the tangent.
     */
    public static Point2d point2dAlongTangent(Point2d startPoint, Vector2d tangent, double distance) {
        // Normalize the tangent vector
        Vector2d normalizedTangent = new Vector2d(tangent);
        normalizedTangent.normalize();

        // Scale the tangent by the distance
        normalizedTangent.scale(distance);

        // Compute the new point
        return new Point2d(
                startPoint.x + normalizedTangent.x,
                startPoint.y + normalizedTangent.y
        );
    }

    public static Coordinates2D convertMmToPixelCoordinates(Point3d point3d, AbstractRenderer renderer) {
        Coordinates2D world_x_y = renderer.coord2pixel(new Coordinates2D(point3d.x, point3d.y));

        double scaledX = world_x_y.getX();
        double scaledY = world_x_y.getY();
        return new Coordinates2D(scaledX, scaledY);
    }



    /**
     * Generates a noise map with a truncated Gaussian effect.
     *
     * @param width           Width of the noise map.
     * @param height          Height of the noise map.
     * @param centerX         X-coordinate of the circle center.
     * @param centerY         Y-coordinate of the circle center.
     * @param circleRadius    Radius of the circle.
     * @param noiseLevel      Noise level within the circle (0-1 range).
     * @param sigmaX          Standard deviation in the x direction for Gaussian outside the circle.
     * @param sigmaY          Standard deviation in the y direction for Gaussian outside the circle.
     * @param background      Background intensity (0 for black, 1 for red).
     * @return A noise map based on the truncated Gaussian effect.
     */
    public static BufferedImage generateTruncatedGaussianNoiseMap(int width, int height,
                                                                  double centerX, double centerY,
                                                                  double circleRadius, double noiseLevel,
                                                                  double sigmaX, double sigmaY,
                                                                  double background) {
        BufferedImage noiseMap = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);

        // Convert the background and noiseLevel values to a 0-255 range for the red component
        int backgroundRed;
        int noiseLevelRed;
        if (noiseLevel > background) {
            backgroundRed = (int) (Math.min(background, 1.0) * 255);
            noiseLevelRed = (int) (Math.min(noiseLevel, 1.0) * 255);
        } else{
            backgroundRed = 0;
            noiseLevelRed = (int) (Math.min(noiseLevel, 1.0) * 255);
        }

        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                double distanceToCenter = Math.sqrt(Math.pow(x - centerX, 2) + Math.pow(y - centerY, 2));

                int redValue = backgroundRed;

                if (distanceToCenter <= circleRadius) {
                    // Within the circle
                    redValue += noiseLevelRed;
                } else {
                    // Calculate Gaussian fade from the circle's edge
                    double offsetDistance = distanceToCenter - circleRadius;
                    double gaussValue = noiseLevel * Math.exp(-0.5 * (Math.pow(offsetDistance / sigmaX, 2) + Math.pow(offsetDistance / sigmaY, 2)));
                    redValue += (int) (Math.min(gaussValue, 1.0) * 255);
                }

                redValue = Math.min(redValue, 255);  // Ensure the value doesn't exceed 255

                // Set the pixel color in the noise map
                Color color = new Color(redValue, 0, 0, 255);
                noiseMap.setRGB(x, y, color.getRGB());
            }
        }
        return noiseMap;
    }

    /**
     * Generates a Gaussian noise map based on the specified parameters.
     *
     * @param width       Width of the noise map.
     * @param height      Height of the noise map.
     * @param centerX     X-coordinate of the Gaussian center.
     * @param centerY     Y-coordinate of the Gaussian center.
     * @param sigmaX      Standard deviation in the x direction.
     * @param sigmaY      Standard deviation in the y direction.
     * @param amplitude   Peak value of the Gaussian (0-1 range).
     * @param background  Background intensity (0 for black, 1 for red).
     * @return A noise map based on the Gaussian function.
     */
    public static BufferedImage generateGaussianNoiseMap(int width, int height,
                                                         double centerX, double centerY,
                                                         double sigmaX, double sigmaY,
                                                         double amplitude, double background) {
        BufferedImage noiseMap = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);

        // Convert the background value to a 0-255 range for the red component
        int backgroundRed = (int) (Math.min(background, 1.0) * 255);

        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                double gaussValue = GaussianFunction.compute2DGaussian(x, y, centerX, centerY,
                        sigmaX, sigmaY, amplitude);

                // Convert the Gaussian value (0-1 range) to a 0-255 range for the red component
                int redValue = (int) (Math.min(gaussValue, 1.0) * 255 + backgroundRed);
                redValue = Math.min(redValue, 255);  // Ensure the value doesn't exceed 255

                // Set the pixel color in the noise map
                Color color = new Color(redValue, 0, 0, 255);
                noiseMap.setRGB(x, y, color.getRGB());
            }
        }
        return noiseMap;
    }

    public int getWidth() {
        return width;
    }

    public void setWidth(int width) {
        this.width = width;
    }

    public int getHeight() {
        return height;
    }

    public void setHeight(int height) {
        this.height = height;
    }

    public double getBackground() {
        return background;
    }

    public void setBackground(double background) {
        this.background = background;
    }

    public boolean isDoEnforceHiddenJunction() {
        return doEnforceHiddenJunction;
    }

    public void setDoEnforceHiddenJunction(boolean doEnforceHiddenJunction) {
        this.doEnforceHiddenJunction = doEnforceHiddenJunction;
    }

    public boolean isDebugMode() {
        return debugMode;
    }

    public void setDebugMode(boolean debugMode) {
        this.debugMode = debugMode;
    }

    public double getPercentRequiredInside() {
        return percentRequiredInside;
    }

    public void setPercentRequiredInside(double percentRequiredInside) {
        this.percentRequiredInside = percentRequiredInside;
    }

    public boolean isOptimizeShiftToHideComps() {
        return optimizeShiftToHideComps;
    }

    public void setOptimizeShiftToHideComps(boolean optimizeShiftToHideComps) {
        this.optimizeShiftToHideComps = optimizeShiftToHideComps;
    }

    public double getTargetInsideFraction() {
        return targetInsideFraction;
    }

    public void setTargetInsideFraction(double targetInsideFraction) {
        this.targetInsideFraction = targetInsideFraction;
    }

    public int getShiftSearchSteps() {
        return shiftSearchSteps;
    }

    public void setShiftSearchSteps(int shiftSearchSteps) {
        this.shiftSearchSteps = shiftSearchSteps;
    }
}