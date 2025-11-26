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
    public void checkInNoise(ProceduralMatchStick proceduralMatchStick, List<Integer> mustBeInNoiseCompIds, double percentRequiredOutsideNoise){
        proceduralMatchStick.setNoiseOrigin(calculateNoiseOrigin(proceduralMatchStick, mustBeInNoiseCompIds));
        debug_noise_origin = new Point2d(proceduralMatchStick.getNoiseOrigin().getX(), proceduralMatchStick.getNoiseOrigin().getY());
        debug_points_vect.clear();
        debug_points_obj1.clear();
        debug_points_outside.clear();

        for (Point3d point : proceduralMatchStick.getObj1().vect_info){
            if (point != null) {
                debug_points_obj1.add(new Point2d(point.getX(), point.getY()));
            }
        }

        ArrayList<ConcaveHull.Point> pointsToCheck = new ArrayList<>();
        Point3d massCenter = proceduralMatchStick.getMassCenter();
        int index = 0;
        for (int mustBeInNoiseCompId : mustBeInNoiseCompIds) {
            AllenTubeComp testingComp = proceduralMatchStick.getComp()[mustBeInNoiseCompId];

            //Must Correct the points here:
            Point3d[] compVect_info = testingComp.getVect_info();
            Point3d[] correctedVect_info = new Point3d[compVect_info.length];

            for (Point3d in : compVect_info) {
                if (in != null) {
                    Point3d correctedPoint = new Point3d(in);
                    correctedPoint.sub(massCenter);
                    correctedPoint.scale(proceduralMatchStick.getScaleForMAxisShape());
                    correctedPoint.add(massCenter);
                    correctedVect_info[index] = correctedPoint;
                    index++;
                }
            }

            index=0;
            for (Point3d point3d : correctedVect_info) {
                if (point3d != null) {
                    debug_points_vect.add(new Point2d(point3d.getX(), point3d.getY()));
                    pointsToCheck.add(new ConcaveHull.Point(point3d.getX(), point3d.getY()));
                    index++;
                }
            }
        }

        int numPointsInside = 0;
        for (ConcaveHull.Point point: pointsToCheck){
            if (isPointWithinCircle(new Point2d(point.getX(), point.getY()), new Point2d(proceduralMatchStick.getNoiseOrigin().getX(), proceduralMatchStick.getNoiseOrigin().getY()), proceduralMatchStick.noiseRadiusMm)){
                numPointsInside++;
            } else{
                debug_points_outside.add(new Point2d(point.getX(), point.getY()));
//                double error = Math.abs(point.distance(new Point2d(proceduralMatchStick.getNoiseOrigin().getX(), proceduralMatchStick.getNoiseOrigin().getY())) - proceduralMatchStick.noiseRadiusMm);
//                System.out.println("OUTSIDE: " + point.getX() + ", " + point.getY()
//                        + " with error: " + error);
            }
        }
        //TODO: potential improvement: we could replace the mechanism for this by somehow identifying points in the junction itself
        double percentRequiredInside = doEnforceHiddenJunction ? 1.0 : 0.95;
        double actualPercentageInside = (double) numPointsInside / pointsToCheck.size();
        if (actualPercentageInside < percentRequiredInside){
            throw new NoiseException("Found points outside of noise circle: " + actualPercentageInside + "% inside + with noise Radius: " + proceduralMatchStick.noiseRadiusMm);
        }

        //Check if enough points not in compId are outside of the noise circle
        ArrayList<Point2d> pointsToCheckIfOutside = new ArrayList<>();
        for (int compIdx = 1; compIdx<= proceduralMatchStick.getnComponent(); compIdx++){
            if (!mustBeInNoiseCompIds.contains(compIdx)){
                Point3d[] compVectInfo = proceduralMatchStick.getComp()[compIdx].getVect_info();
                index = 0;
                for (Point3d point3d: compVectInfo){
                    if (point3d != null){
                        if (index % 1 == 0) //For speed, we only check every other point for the hull
                            pointsToCheckIfOutside.add(new Point2d(point3d.getX(), point3d.getY()));
                        index++;
                    }
                }
            }
        }

        int numPointsOutside = 0;
        for (Point2d point: pointsToCheckIfOutside){
            if (!isPointWithinCircle(point, new Point2d(proceduralMatchStick.getNoiseOrigin().getX(), proceduralMatchStick.getNoiseOrigin().getY()), proceduralMatchStick.noiseRadiusMm)){
                numPointsOutside++;
            }
        }
        double percentOutside = (double) numPointsOutside / pointsToCheckIfOutside.size();
        System.out.println("%%%% OUTSIDE: " + percentOutside);
        if (percentOutside < percentRequiredOutsideNoise){
            throw new NoiseException("Not enough points outside of noise circle");
        }
        System.out.println("SUCCEEDED CHECK IN NOISE");
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
                            return calcProjectionFromSingleJunctionWithSingleComp(proceduralMatchStick, baseCompId, junc);
                        } else if (junc.getnComp() > 2) {
                            return calcProjectionFromJunctionWithMultiComp(proceduralMatchStick, specialCompId, junc);
                        } else{
                            throw new IllegalArgumentException("Junction has less than 2 components");
                        }
                    }
                }
            }
        } else{
            int baseCompId = -1;
            for (int i = 1; i<= proceduralMatchStick.getnComponent(); i++){
                if (!compsToBeInNoise.contains(i)){
                    baseCompId = i;
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
                        return calcProjectionFromSingleJunctionWithSingleComp(proceduralMatchStick, baseCompId, junc);
                    }
                }
            }

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
    public Point3d calcProjectionFromSingleJunctionWithSingleComp(ProceduralMatchStick proceduralMatchStick, Integer baseCompId, JuncPt_struct junc) {
        Point3d projectedPoint;

        // Find tangent to project along for noise origin
        proceduralMatchStick.projectedTangent = getJuncTangentForSingle(proceduralMatchStick, junc, baseCompId);
        proceduralMatchStick.projectedTangent = new Vector3d(proceduralMatchStick.projectedTangent.x, proceduralMatchStick.projectedTangent.y, 0);

        // Choose a starting point
        Point3d startingPosition = chooseStartingPoint(junc, proceduralMatchStick.projectedTangent, proceduralMatchStick.getScaleForMAxisShape());
        System.out.println("Starting position: " + startingPosition);
        projectedPoint = pointAlong2dTangent(startingPosition,
                proceduralMatchStick.projectedTangent,
                proceduralMatchStick.noiseRadiusMm);
        return projectedPoint;
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
    public Point3d calcProjectionFromJunctionWithMultiComp(ProceduralMatchStick proceduralMatchStick, Integer specialCompId, JuncPt_struct junc) {
        Point3d projectedPoint;
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
                double externalAngle = 2*Math.PI - tangent1.angle(tangent2);
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
        bisector.negate();
        Vector3d bisector_3d = new Vector3d(bisector.getX(), bisector.getY(), 0);
        proceduralMatchStick.projectedTangent = bisector_3d;

        Point3d startingPosition = chooseStartingPoint(junc, bisector_3d, proceduralMatchStick.getScaleForMAxisShape());
        projectedPoint = pointAlong2dTangent(startingPosition, bisector_3d, proceduralMatchStick.noiseRadiusMm);
        return projectedPoint;
    }

    public Point3d chooseStartingPoint(JuncPt_struct junc, Vector3d tangent, double scaleForMAxisShape) {
        Vector3d reverseTangent = new Vector3d(tangent);
        reverseTangent.negate(); //reverse so we end up with a point inside of the shape
        double shiftAmount = doEnforceHiddenJunction ? junc.getRad() * scaleForMAxisShape : 0.0;
        Point3d startingPosition = choosePositionAlongTangent(
                reverseTangent,
                junc.getPos(), //this is shifted by applyTranslation
                shiftAmount); // this is not shifted by smoothize
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
                                                            AbstractRenderer renderer, List<Integer> specialCompIndcs){

        Point3d noiseOrigin = calculateNoiseOrigin(mStick, specialCompIndcs);


//        double sigmaPixels = mmToPixels(renderer, mStick.noiseRadiusMm/6);
        double sigmaPixels = mmToPixels(renderer, mStick.noiseRadiusMm/12);
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
}