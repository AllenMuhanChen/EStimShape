package org.xper.allen.drawing.composition.experiment;

import org.xper.allen.drawing.composition.AllenTubeComp;
import org.xper.allen.drawing.composition.morph.*;
import org.xper.allen.drawing.composition.noisy.GaussianNoiseMapper;
import org.xper.allen.drawing.composition.noisy.NAFCNoiseMapper;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.allen.util.CoordinateConverter;
import org.xper.allen.util.CoordinateConverter.SphericalCoordinates;
import org.xper.drawing.stick.JuncPt_struct;
import org.xper.drawing.stick.stickMath_lib;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;
import java.util.*;

/**
 * Matchsticks procedurally generated from base components, and delta versions of those matchsticks
 *
 * contains ability to generate noisemaps
 * Noiseable
 */
public class ProceduralMatchStick extends GAMatchStick {

    protected double[] PARAM_nCompDist = {0, 0.33, 0.67, 1.0, 0.0, 0.0, 0.0, 0.0};
    //protected double[] PARAM_nCompDist = {0, 0, 1, 0, 0.0, 0.0, 0.0, 0.0};
    protected SphericalCoordinates objCenteredPositionTolerance =
            new SphericalCoordinates(0.5, Math.PI / 8, Math.PI / 3 );
    public double noiseRadiusMm = 20;
    public int maxAttempts = 5;
    private Point3d noiseOrigin;
    public Vector3d projectedTangent;
    public NAFCNoiseMapper noiseMapper;

    public boolean noiseDebugMode = false;

    public ProceduralMatchStick(NAFCNoiseMapper noiseMapper) {
        this.noiseMapper = noiseMapper;
    }

    /**
     * Generates a new matchStick from the base matchStick's driving component
     *
     * @param baseMatchStick
     * @param morphComponentIndx
     * @param nComp if 0, then choose randomly
     * @param maxAttempts
     */
    public void genMatchStickFromComponent(ProceduralMatchStick baseMatchStick, int morphComponentIndx, int nComp, int maxAttempts) {
        // calculate the object centered position of the base matchStick's drivingComponent
//        Map<Integer, SphericalCoordinates> objCenteredPosForDrivingComp =
//                calcObjCenteredPosForDrivingComp(baseMatchStick, drivingComponentIndex);
        if (nComp == 0){
            nComp = chooseNumComps();
        }
        int numAttempts = 0;
        while (numAttempts < maxAttempts || maxAttempts == -1) {
            System.out.println("ATtempting genMatchFromLeaf: " + numAttempts);
            if (genMatchStickFromLeaf(morphComponentIndx, baseMatchStick, nComp)) {
                return;
            } else{
                numAttempts++;
            }
        }
        throw new MorphRepetitionException("Could not generate matchStick FROM DRIVING COMPONENT after " + maxAttempts + " attempts");
    }



    public void genMorphedDrivingComponentMatchStick(ProceduralMatchStick baseMatchStick, double magnitude, double discreteness, boolean doPositionShape, boolean doCheckNoise, int maxAttempts) {
        int drivingComponentIndx = baseMatchStick.getSpecialEndComp().get(0);
        int numAttempts = 0;
        this.maxAttempts = baseMatchStick.maxAttempts;
        while (numAttempts < this.maxAttempts || this.maxAttempts == -1) {
            try {
                genNewComponentMatchStick(baseMatchStick, drivingComponentIndx, magnitude, discreteness, doPositionShape, 15);
            } catch(MorphException e) {
                System.out.println(e.getMessage());
                continue;
            } finally{
                numAttempts++;
            }

            checkMStickSize();
            break;
        }

    }

    public void genNewComponentMatchStick(ProceduralMatchStick baseMatchStick, int morphComponentIndx, double magnitude, double discreteness, boolean doPositionShape, int maxAttempts) {
        Map<Integer, ComponentMorphParameters> morphParametersForComponents = new HashMap<>();
        //TODO: could refractor ComponentMorphParameters into data class and factory for different applications
        morphParametersForComponents.put(morphComponentIndx, new NormalDistributedComponentMorphParameters(magnitude, new NormalMorphDistributer(discreteness)));

        int numAttempts = 0;
        while ((numAttempts < maxAttempts || maxAttempts == -1)) {
            try {
                genMorphedComponentsMatchStick(morphParametersForComponents, baseMatchStick, doPositionShape, null, null);
            } catch(MorphException e) {
                System.out.println(e.getMessage());
                continue;
            } finally{
                numAttempts++;
            }

//            checkMStickSize();
            break;
        }
        if (numAttempts >= maxAttempts && maxAttempts != -1) {
            throw new MorphRepetitionException("Could not generate matchStick WITH NEW DRIVING COMP after " + maxAttempts + " attempts");
        }
    }

    protected void positionShape() {
    }

    public void genMatchStickFromComponentInNoise(ProceduralMatchStick baseMatchStick, int fromCompId, int nComp, boolean doCompareObjCenteredPos, int maxAttempts1, NAFCNoiseMapper noiseMapper) {
        this.maxAttempts = maxAttempts1;
        if (nComp == 0){
            nComp = chooseNumComps();
        }
        int nAttempts = 0;
        while (nAttempts < this.maxAttempts || this.maxAttempts == -1) {
            nAttempts++;
            try {
                genMatchStickFromComponent(baseMatchStick, fromCompId, nComp, this.maxAttempts);
            } catch (MorphException e){
                System.out.println("Error with morph, retrying");
                System.out.println(e.getMessage());
                continue;
            }
            int drivingComponent = getDrivingComponent();
            List<Integer> compsToNoise = Collections.singletonList(drivingComponent);
            try {
                this.noiseMapper = noiseMapper;
                this.noiseMapper.checkInNoise(this, compsToNoise, 0.5);
            } catch (Exception e) {
                if (noiseDebugMode){
                    return;
                }
                System.out.println("Error with noise, retrying");
                System.out.println(e.getMessage());
                continue;
            }
            SphericalCoordinates originalObjCenteredPos = calcObjCenteredPosForComp(baseMatchStick, fromCompId);
            SphericalCoordinates newDrivingObjectCenteredPos = calcObjCenteredPosForComp(this, drivingComponent);
            if (doCompareObjCenteredPos)
                try {
                    compareObjectCenteredPositions(originalObjCenteredPos, newDrivingObjectCenteredPos);
                } catch (MorphException e) {
                    System.out.println(e.getMessage());
                }
            return;
        }
        throw new MorphRepetitionException("Could not generate matchStick FROM COMPONENT IN NOISE after " + this.maxAttempts + " attempts");
    }

    public int assignDeltaCompId() {
        int drivingComponent = getDrivingComponent();
        List<Integer> allComps = getCompIds();
        decideLeafBranch();
        boolean[] leafBranch = getLeafBranch();

        List<Integer> elegibleComps = new LinkedList<>();
        for (Integer compId : allComps) {
            if (compId != drivingComponent) {
                if (leafBranch[compId]) {
                    elegibleComps.add(compId);
                }
            }
        }

        //choose a random one
        int randIndex = (int) (Math.random() * elegibleComps.size());
        int deltaCompId = elegibleComps.get(randIndex);
        return deltaCompId;
    }

    public Integer getDrivingComponent() {
        return getSpecialEndComp().get(0);
    }

    public void setNoiseOrigin(Point3d noiseOrigin) {
        this.noiseOrigin = noiseOrigin;
    }

//    protected boolean validMStickSize() {
////        double buffer = 0.5; //in degrees, on each side. So total buffer is 1 degree
//        double maxRadius = getScaleForMAxisShape(); // degree
//        int i, j;
//
//        for (i = 1; i <= getnComponent(); i++) {
//            for (j = 1; j <= getComp()[i].getnVect(); j++) {
//                double xLocation = getComp()[i].getVect_info()[j].x;
//                double yLocation = getComp()[i].getVect_info()[j].y;
//
//                if(xLocation > maxRadius || xLocation < -maxRadius){
////					System.err.println("TOO BIG");
////					System.err.println("xLocation is: " + xLocation + ". maxBound is : " + maxRadius);
//                    return false;
//                }
//                if(yLocation > maxRadius || yLocation < -maxRadius){
////					System.err.println("TOO BIG");
////					System.err.println("yLocation is: " + yLocation + ". maxBound is : " + maxRadius);
//                    return false;
//                }
//            }
//        }
//        return true;
//    }

    public static class MorphRepetitionException extends MorphException{
        public MorphRepetitionException(String message){
            super(message);
        }
    }

    protected Map<Integer, SphericalCoordinates> calcObjCenteredPosMapForComp(ProceduralMatchStick baseMatchStick, int drivingComponentIndex) {
        Point3d shapeMassCenter = baseMatchStick.getMassCenter();
        Point3d drivingComponentMassCenter = baseMatchStick.getMassCenterForComponent(drivingComponentIndex);
        Point3d drivingComponentObjectCenteredPositionPoint = new Point3d(drivingComponentMassCenter);
        drivingComponentObjectCenteredPositionPoint.sub(shapeMassCenter);
        SphericalCoordinates drivingComponentObjectCenteredPosition = CoordinateConverter.cartesianToSpherical(drivingComponentObjectCenteredPositionPoint);
        Map<Integer, SphericalCoordinates> objCenteredPosForDrivingComp = new HashMap<>();
        objCenteredPosForDrivingComp.put(drivingComponentIndex, drivingComponentObjectCenteredPosition);
        return objCenteredPosForDrivingComp;
    }

    public static SphericalCoordinates calcObjCenteredPosForComp(ProceduralMatchStick matchStick, int compId) {
        Point3d shapeMassCenter = matchStick.getMassCenter();
        Point3d drivingComponentMassCenter = matchStick.getMassCenterForComponent(compId);
        Point3d drivingComponentObjectCenteredPositionPoint = new Point3d(drivingComponentMassCenter);
        drivingComponentObjectCenteredPositionPoint.sub(shapeMassCenter);
        return CoordinateConverter.cartesianToSpherical(drivingComponentObjectCenteredPositionPoint);
    }

    /**
     * Generates a new matchStick from morphing the base component in the targetMatchStick
     *
     * @param targetMatchStick
     * @param maxAttempts
     * @param doPositionShape
     * @param doCompareObjCenteredPos
     */
    public void genMorphedBaseMatchStick(ProceduralMatchStick targetMatchStick,
                                         int drivingComponentIndex,
                                         int maxAttempts,
                                         boolean doPositionShape,
                                         boolean doCompareObjCenteredPos) {
        int baseComponentIndex;
        List<Integer> baseCompIndcs = new LinkedList<>();
        for (int compId : targetMatchStick.getCompIds()) {
            if (compId != drivingComponentIndex) {
                baseCompIndcs.add(compId);
            }
        }


        //TODO: could refractor ComponentMorphParameters into data class and factory for different applications
        SphericalCoordinates originalObjCenteredPos = calcObjCenteredPosForComp(targetMatchStick, drivingComponentIndex);

        int nAttempts = 0;
        while (nAttempts < maxAttempts || maxAttempts == -1) {
            try {
                nAttempts++;
                Map<Integer, ComponentMorphParameters> morphParametersForComponents = new HashMap<>();
                BaseMorphParameters morphParams = new BaseMorphParameters();
                for (int i = 0; i < baseCompIndcs.size(); i++) {
                    baseComponentIndex = baseCompIndcs.get(i);
                    morphParametersForComponents.put(baseComponentIndex, morphParams);
                }
                genMorphedComponentsMatchStick(morphParametersForComponents, targetMatchStick, doPositionShape, null, null);
                SphericalCoordinates newDrivingObjectCenteredPos = calcObjCenteredPosForComp(this, drivingComponentIndex);
                if (doCompareObjCenteredPos)
                    compareObjectCenteredPositions(originalObjCenteredPos, newDrivingObjectCenteredPos);
                checkLeafBaseRatio();
                return;
            } catch (ObjectCenteredPositionException e) {
                cleanData();
                this.setObj1(null);
                System.out.println("Error with object centered position, retrying");
                System.out.println(e.getMessage());
            } catch (MorphException e) {
                e.printStackTrace();
                cleanData();
                this.setObj1(null);
            }
        }

        if (nAttempts >= maxAttempts && maxAttempts != -1) {
            throw new MorphRepetitionException("Could not generate matchStick FROM BASE COMPONENT after " + this.maxAttempts + " attempts");
        }
    }

    private void checkLeafBaseRatio() {
        int leafIndx = getDrivingComponent();
        boolean succeed = vetLeafBaseSize(leafIndx);
        if (!succeed){
            throw new MorphException("Leaf to Base Size Ratio Check Failed");
        }
    }

    public void compareObjectCenteredPositions(SphericalCoordinates expected, SphericalCoordinates actual) {
        double rPercentDifference = Math.abs(actual.r - expected.r) / expected.r;
        if (rPercentDifference > objCenteredPositionTolerance.r ||
                angleDiff(actual.theta, expected.theta) > objCenteredPositionTolerance.theta ||
                angleDiff(actual.phi, expected.phi) > objCenteredPositionTolerance.phi) {
            throw new ObjectCenteredPositionException("Object Centered Position is off");
        }
    }

    public static void compareObjectCenteredPositions(SphericalCoordinates expected, SphericalCoordinates actual, SphericalCoordinates tolerances) {
        double rPercentDifference = Math.abs(actual.r - expected.r) / expected.r;
        System.out.println("rPercentDifference: " + rPercentDifference);
        System.out.println("angleDiff theta: " + angleDiff(actual.theta, expected.theta));
        System.out.println("angleDiff phi: " + angleDiff(actual.phi, expected.phi));
        if (rPercentDifference > tolerances.r ||
                angleDiff(actual.theta, expected.theta) > tolerances.theta ||
                angleDiff(actual.phi, expected.phi) > tolerances.phi) {
            throw new ObjectCenteredPositionException("Object Centered Position is off");
        }
    }

    protected Vector3d centerSpecialJunctionAtOrigin(){
        Point3d origin = new Point3d(0,0,0);
        Point3d specialJunctionPos = new Point3d(0,0,0);
        for (JuncPt_struct junc : getJuncPt()) {
            if (junc != null) {
                int numMatch = Arrays.stream(junc.getCompIds()).filter(x -> x == 1).toArray().length;
                if (numMatch == 1) {
                    specialJunctionPos = junc.getPos();
                }
            }
        }

        Vector3d shiftVec = new Vector3d();
        shiftVec.sub(origin, specialJunctionPos);
        applyTranslation(shiftVec);
        return shiftVec;
    }

    public Point3d getMassCenterForComponent(int componentIndex) {
        Point3d cMass = new Point3d(0, 0, 0);
        AllenTubeComp targetComp = getComp()[componentIndex];
        int totalVect = targetComp.getnVect();
        for (int i = 1; i <= totalVect; i++) {
            cMass.add(targetComp.getVect_info()[i]);
        }
        cMass.x /= totalVect;
        cMass.y /= totalVect;
        cMass.z /= totalVect;
        return cMass;
    }
    public static class ObjectCenteredPositionException extends MorphException{

        public ObjectCenteredPositionException(String message){
            super(message);
        }
    }

    /**
     * DEPRECRATED. Just not removing to avoid breaking some tests.
     * @param specialCompId
     * @return
     */
    public Point3d calculateGaussNoiseOrigin(int specialCompId) {
        return ((GaussianNoiseMapper)noiseMapper).calculateNoiseOrigin(this, Collections.singletonList(specialCompId));
//        Point3d point3d = new Point3d();
//        for (JuncPt_struct junc : getJuncPt()) {
//            if (junc != null) {
//                int numMatch = Arrays.stream(junc.getCompIds()).filter(x -> x == specialCompId).toArray().length;
//                if (numMatch == 1) {
//                    if (junc.getnComp() == 2) {
//                        point3d = calcProjectionFromSingleJunctionWithSingleComp(specialCompId, junc);
//                    } else if (junc.getnComp() > 2){
//                        point3d = calcProjectionFromJunctionWithMultiComp(specialCompId, junc);
//                    }
//                }
//            }
//        }
//
//        return point3d;
    }

    public static int findBaseCompId(Integer specialCompIndx, JuncPt_struct junc) {
        int baseCompId = -1;
        int[] connectedComps = junc.getCompIds();
        for (int comp : connectedComps) {
            if (comp != specialCompIndx && comp != 0) {
                baseCompId = comp;
            }
        }
        return baseCompId;
    }

    private Point3d choosePositionAlongMAxisFromJuncUNdx(int junctionUNdx, Point3d[] connectedMpts, int distanceFromJunction) {
        Point3d startingPosition;
        if (junctionUNdx == 1) {
            startingPosition = connectedMpts[1+ distanceFromJunction];
        } else {
            startingPosition = connectedMpts[51- distanceFromJunction];
        }
        return startingPosition;
    }

    public void genMatchStickRand() {
        int nComp = chooseNumComps();
        genMatchStickRand(nComp);
    }

    public static int chooseNumComps() {
        int nComp;
        ProceduralMatchStick tempStick = new ProceduralMatchStick(null);
        double[] nCompDist = tempStick.getPARAM_nCompDist();
        nComp = stickMath_lib.pickFromProbDist(nCompDist);
        return nComp;
    }

    public void genMatchStickRand(int nComp) {
        while (true) {
            while (true) {
                if (genMatchStick_comp(nComp)) {
                    break;
                }
            }

            centerShape();
            boolean res = smoothizeMStick();
            res = res && validMStickSize();
            if (res) {
                break;
            }// else we need to gen another shape
        }
    }

    @Override
    public double[] getPARAM_nCompDist() {
        return PARAM_nCompDist;
    }

    public void setMaxAttempts(int maxAttempts) {
        this.maxAttempts = maxAttempts;
    }

    public Point3d getNoiseOrigin() {
        return noiseOrigin;
    }
}