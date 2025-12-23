package org.xper.allen.drawing.composition.morph;

import org.xper.allen.drawing.composition.AllenMAxisArc;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.AllenTubeComp;
import org.xper.allen.util.CoordinateConverter;
import org.xper.drawing.stick.EndPt_struct;
import org.xper.drawing.stick.JuncPt_struct;
import org.xper.drawing.stick.stickMath_lib;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;
import java.util.*;
import java.util.function.BiConsumer;
import java.util.function.Consumer;

import static org.xper.allen.drawing.composition.experiment.ProceduralMatchStick.compareObjectCenteredPositions;
import static org.xper.allen.drawing.ga.GAMatchStick.calcObjCenteredPosForComp;
import static org.xper.allen.drawing.ga.GAMatchStick.objCenteredPositionTolerance;

public class MorphedMatchStick extends AllenMatchStick {
    public static CoordinateConverter.SphericalCoordinates objCenteredPositionTolerance =
            new CoordinateConverter.SphericalCoordinates(0.5, Math.PI/4, Math.PI / 2);

    protected int MAX_TOTAL_ATTEMPTS = 15;
    private final double PROB_addToEndorJunc = 1.0; // x% add to end or JuncPt, 1-x% add to branch
    private final double PROB_addToEnd_notJunc = 0.5; // when "addtoEndorJunc",
    // 50% add to end, 50%
    // add to junc
    public double[] PARAM_nCompDist = {0, 0.33, 0.67, 1.0, 0.0, 0.0, 0.0, 0.0 };
    //    protected final double[] PARAM_nCompDist = {0, 0.33, 0.66, 1.0, 0.0, 0.0, 0.0, 0.0 };
//    protected final double[] PARAM_nCompDist = {0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 };
//    protected final double[] PARAM_nCompDist = {0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0 };
    protected final double PROB_addTiptoBranch = 0; 	// when "add new component to the branch is true"
    private double TangentSaveZone = 0; //Should be zero here, because we're manually specifying a new tangent
    // with the morph parameters, so we don't need to check the relation to the old tangent.

    private static final int NUM_ATTEMPTS_PER_COMPONENT = 15;
    private static final int NUM_ATTEMPTS_PER_SKELETON = 2;
    private static final int NUM_ATTEMPTS_PER_ARC = 2;
    private static final double NUM_ATTEMPTS_PER_RADIUS_PROFILE = 2;
    protected AllenMAxisArc newArc;
    private int[] compLabel;
    private MorphedMatchStick localBackup;
    private List<Integer> compsToPreserve = new ArrayList<>();
    public boolean preserveJunction = true; //whether to preserve radii of junctions that contain compsToPreserve
    public MorphData morphData = new MorphData();
    public boolean compareObjectCenteredPosition = false;
    public void genMorphedComponentsMatchStick(Map<Integer, ComponentMorphParameters> morphParametersForComponents, MorphedMatchStick matchStickToMorph, boolean doPositionShape, Boolean preserveJunction, Boolean compareObjectCenteredPosition){
        //default behavior if preserveJunction Param not given: don't preserve juncs
        if(preserveJunction != null){
            this.preserveJunction = preserveJunction;
        }
        if(compareObjectCenteredPosition != null){
            this.compareObjectCenteredPosition = compareObjectCenteredPosition;
        }

        this.showComponents = false;

        localBackup = new MorphedMatchStick();
        localBackup.copyFrom(matchStickToMorph);
        copyFrom(localBackup);


        // Attempt to morph every component. If we fail, then restart with the backup.
        int numAttempts = 0;
        while (numAttempts < getMaxTotalAttempts()) {
            try {
                System.out.println("Attempting to genMorpheedComponechStick");
                numAttempts++;

                findCompsToPreserve(morphParametersForComponents.keySet());

                //TODO: expand to also store and check more than one compsToMorph


                morphAllComponents(morphParametersForComponents);
//                MutateSUB_reAssignJunctionRadius();
                centerShape();
                applyRadiusProfile();
                attemptSmoothizeMStick();

                if (doPositionShape) {
                    positionShape();
                }

                if (this.compareObjectCenteredPosition){
                    int compIndxToPreserve = compsToPreserve.get(0);
                    CoordinateConverter.SphericalCoordinates originalObjCenteredPos = calcObjCenteredPosForComp(matchStickToMorph, compIndxToPreserve);

                    CoordinateConverter.SphericalCoordinates newDrivingObjectCenteredPos = calcObjCenteredPosForComp(this, compIndxToPreserve);
                    compareObjectCenteredPositions(originalObjCenteredPos, newDrivingObjectCenteredPos, objCenteredPositionTolerance);
                }
                return;
            } catch (Exception e) {
                cleanData();
                this.setObj1(null);
                copyFrom(localBackup);
//                e.printStackTrace();
                System.err.println(e.getMessage());
                System.out.println("Failed to morph matchstick.");
                System.out.println("Retrying to morph matchstick...");
            }
        }
        if (numAttempts >= getMaxTotalAttempts()) {
            throw new MorphException("Failed to morph matchstick after " + getMaxTotalAttempts() + " attempts.");
        }
    }

    public void genAddedLimbsMatchStick(MorphedMatchStick matchStickToMorph, int nCompsToAdd) {
        this.showComponents = false;

        MorphedMatchStick backup = new MorphedMatchStick();
        backup.copyFrom(matchStickToMorph);
        copyFrom(backup);


        // Attempt to morph every component. If we fail, then restart with the backup.
        int numAttempts = 0;
        while (numAttempts < getMaxTotalAttempts()) {
            try {
                System.out.println("Attempting to add limbs to matchstick");
                numAttempts++;
                addComps(nCompsToAdd);
                updateEndPtsAndJunctionPositions();
                centerShape();
                applyRadiusProfile();
                attemptSmoothizeMStick();
                positionShape();
                System.out.println("Successfully added limbs to matchstick");
                return;
            } catch (MorphException e) {
                cleanData();
                this.setObj1(null);
                copyFrom(backup);
//                e.printStackTrace();
                System.err.println(e.getMessage());
                System.out.println("Failed to morph matchstick.");
                System.out.println("Retrying to morph matchstick...");
            }
        }
        if (numAttempts >= getMaxTotalAttempts()) {
            throw new MorphException("Failed to add limbs to matchstick after " + getMaxTotalAttempts() + " attempts.");
        }
    }

    private void addComps(int numCompsToAdd) {
        if (numCompsToAdd == 0) {
            return;
        }
        int currentNComps = getnComponent();
        int nextCompId = currentNComps + 1;
        int targetNComps = currentNComps + numCompsToAdd;
        for (int i=nextCompId; i<=targetNComps; i++){
            getComp()[i] = new AllenTubeComp();
        }
        setnComponent(targetNComps);
        double randNdx;
        boolean addSuccess;
        while (true)
        {
            if ( showDebug) {
                System.out.println("adding new MAxis on, now # " +  nextCompId);
            }
            int type;
            randNdx = stickMath_lib.rand01();
            if (randNdx < getPROB_addToEndorJunc())
            {
                if (getnJuncPt() == 0 || stickMath_lib.rand01() < getPROB_addToEnd_notJunc()) {
                    type=1;
                    addSuccess = Add_MStick(nextCompId, type);
                } else {
                    type=2;
                    addSuccess = Add_MStick(nextCompId, type);
                }
            }
            else
            {
                if (stickMath_lib.rand01() < getPROB_addTiptoBranch()) {
                    type=3;
                    addSuccess = Add_MStick(nextCompId, type);
                }
                else {
                    type=4;
                    addSuccess = Add_MStick(nextCompId, type);
                }
            }
            if (addSuccess) { // otherwise, we'll run this while loop again, and re-generate this component
                getMorphData().addAddedComp(nextCompId, type);
                if (nextCompId == targetNComps)
                    break;
                nextCompId++;
            }

        }

        //up to here, the eligible skeleton should be ready
        // Assign the radius value
        RadiusAssign(currentNComps); // preserve radii of the original components
        // Apply the radius value onto each new component
        for (int i=currentNComps; i<=getnComponent(); i++)
        {
            if( getComp()[i].RadApplied_Factory() == false) // a fail application
            {
                throw new MorphException("Radius profile failed when attempting to be applied to component " + i);
            }
        }
    }

    public void genRemovedLimbsMatchStick(MorphedMatchStick matchStickToMorph, Set<Integer> componentsToRemove){
        this.showComponents = false;

        MorphedMatchStick backup = new MorphedMatchStick();
        backup.copyFrom(matchStickToMorph);
        copyFrom(backup);


        int numAttempts = 0;
        while (numAttempts < getMaxTotalAttempts()) {
            try {
                decideLeafBranch();
                boolean[] removeFlags = new boolean[getnComponent()+1];
                for (int i=1; i<=getnComponent(); i++){
                    if (componentsToRemove.contains(i)){
                        if (getLeafBranch()[i])
                            removeFlags[i] = true;
                        else {
                            System.err.println("ERROR, you have specified a branch to remove, not a leaf." +
                                    "Not removing.");
                            componentsToRemove.remove(i);
                        }
                    }
                }
                removeComponent(removeFlags);
                for (int i=1; i<=getnComponent(); i++){
                    if (removeFlags[i]){
                        getMorphData().addRemovedComp(i);
                    }
                }
                updateEndPtsAndJunctionPositions();
                centerShape();
                applyRadiusProfile();
                attemptSmoothizeMStick();
                positionShape();
                break;
            } catch (MorphException e) {
                cleanData();
                this.setObj1(null);
                copyFrom(backup);
//                e.printStackTrace();
                System.err.println(e.getMessage());
                System.out.println("Failed to gen limb removed matchstick.");
                System.out.println("Retrying to remove limbs...");
            } finally{
                numAttempts++;
//                System.out.println("Attempt " + numAttempts + " of " + MAX_TOTAL_ATTEMPTS + " to morph matchstick");
            }
        }
        if (numAttempts >= getMaxTotalAttempts()) {
            throw new MorphException("Failed gen limb removed matchstick after " + getMaxTotalAttempts() + " attempts.");
        }
    }

    public void checkMStickSize() throws MStickSizeException {
        boolean success = this.validMStickSize();
        if (!success) {
            throw new MStickSizeException("MatchStick size is invalid");
        }
    }



    @Override
    public void genMatchStickRand() {
        int nComp;
//		 double[] nCompDist = { 0, 0.05, 0.15, 0.35, 0.65, 0.85, 0.95, 1.00};
//		 double[] nCompDist = { 0, 0.1, 0.2, 0.4, 0.6, 0.8, 0.9, 1.00};
        // double[] nCompDist = {0, 0.05, 0.15, 0.35, 0.65, 0.85, 0.95, 1.00};
        double[] nCompDist = getPARAM_nCompDist();
        nComp = stickMath_lib.pickFromProbDist(nCompDist);
        // nComp = 2;

        // debug
        // nComp = 4;

        // The way we write like this can guarantee that we try to
        // generate a shape with "specific" # of components

        genMatchStickRand(nComp);

    }

    public void genMatchStickRand(int nComp) {
        while (true) {

            while (true) {
//				System.err.println("Try Rand");
                if (genMatchStick_comp(nComp)) {
                    break;
                }
            }

            int specialCompIndx = (int) (Math.random() * getnComponent() + 1);
            this.setSpecialEndComp(Collections.singletonList(specialCompIndx));

            centerShape();

            boolean smoothSucceeded = smoothizeMStick();


            if (!smoothSucceeded) // fail to smooth
            {
                continue; // else we need to gen another shape
            }

            positionShape();
            try {
                checkMStickSize();
            } catch (MStickSizeException e) {
                continue;
            }
            break;
        }
    }

    private void findCompsToPreserve(Set<Integer> morphParametersForComponents) {
        if (!compsToPreserve.isEmpty()){
            return;
        }
        compsToPreserve.clear();
        List<Integer> components = getCompIds();

        // Determine what components should be preserved
        for (Integer component : components){
            if (!morphParametersForComponents.contains(component)){
                compsToPreserve.add(component);
            }
        }
    }

    public List<Integer> getCompIds() {
        List<Integer> components = new LinkedList<>();
        for (int i = 0; i < getComp().length; i++) {
            if (getComp()[i] != null) {
                components.add(i);
            }
        }
        return components;
    }

    private void morphAllComponents(Map<Integer, ComponentMorphParameters> morphParametersForComponents) {
        System.out.println("Attempting to morph " + morphParametersForComponents.size() + " components.");
        final int[] numSuccessfulMorphs = {0};
        morphParametersForComponents.forEach(new BiConsumer<Integer, ComponentMorphParameters>() {
            @Override
            public void accept(Integer componentIndex, ComponentMorphParameters morphParams) {
                attemptToMorphComponent(componentIndex, morphParams);
                numSuccessfulMorphs[0]++;
                System.out.println("Successfully morphed " + numSuccessfulMorphs[0] + " components out of " + morphParametersForComponents.size() + " components.");
                getMorphData().addDataForComp(componentIndex, morphParams.getMorphData());
            }
        });
    }

    /**
     * Makes several attempts to morph a single component given a set of morph parameters.
     * If any attempt fails, it will load a backup of the matchstick and try again.
     * If all attempts fail, it will throw a MorphException.

     */
    private void attemptToMorphComponent(Integer componentIndex, ComponentMorphParameters morphParams) {
        localBackup = new MorphedMatchStick();
        localBackup.copyFrom(this);

        int numAttempts=0;
        while (numAttempts < NUM_ATTEMPTS_PER_COMPONENT) {
            try {
//                if (this.getComp()[componentIndex].getmAxisInfo().getRad() >= 1000) {
//                    System.out.println("Redistributing Rotation");
//                    ((NormalDistributedComponentMorphParameters)morphParams).redistributeRotationMagntiude();
//                }
                morphComponent(componentIndex, morphParams);
                System.out.println("Successfully morphed component " + componentIndex);
                return;
            } catch (MorphException e) {
                System.err.println(e.getMessage());
                System.out.println("Failed to Morph Component " + componentIndex + " with parameters " + morphParams + " because of " + e.getMessage());
                morphParams.distribute();
                copyFrom(localBackup);
            } finally {
                numAttempts++;
            }
        }
        throw new MorphException("Did not successfully morph component " + componentIndex + " after " + NUM_ATTEMPTS_PER_COMPONENT + " attempts.");
    }

    private void morphComponent(int id, ComponentMorphParameters morphParams) throws MorphException{
        compLabel = MutationSUB_compRelation2Target(id);
        attemptToGenerateValidComponentSkeleton(id, morphParams);
        updateEndPtsAndJunctionPositions();
        attemptMutateRadius(id, morphParams);
        checkForTubeCollisions();
        if (this.maxDiameterDegrees != null){
            mStickFitsInBox(maxDiameterDegrees);
        }
    }

    private void attemptToGenerateValidComponentSkeleton(int id, ComponentMorphParameters morphParams) {
        int numAttempts = 0;
        while(numAttempts < NUM_ATTEMPTS_PER_SKELETON){
            try {
                newArc = attemptToGenerateValidMorphedArc(id, morphParams);
                updateJuncPtsForNewComp(id);
                updateComponentInfo(id);
                checkForCollisions(id);
                return;
            } catch (MorphException e){
                copyFrom(localBackup);
                System.err.println(e.getMessage());
            } finally {
                numAttempts++;
            }
        }
        throw new MorphException("Failed to generate valid skeleton for using a morphed component " + id + " after " + NUM_ATTEMPTS_PER_SKELETON + " attempts.");
    }

    protected void updateComponentInfo(int id) {
        boolean branchUsed = getComp()[id].isBranchUsed();
        int connectType = getComp()[id].getConnectType();
        double[][] oldRadInfo = getComp()[id].getRadInfo();

        addTube(id);
        getComp()[id].setRadInfo(oldRadInfo);
        getComp()[id].getmAxisInfo().copyFrom(newArc);
        getComp()[id].setBranchUsed(branchUsed);
        getComp()[id].setConnectType(connectType);

    }

    public void attemptSmoothizeMStick() {
        boolean res;
        try{
            res = smoothizeMStick();
        } catch(Exception e){
            e.printStackTrace();
            throw new MorphException("Failed to smoothize the matchstick!");
        }
        if(!res){
            throw new MorphException("Failed to smoothize the matchstick!");
        }

    }

    private void checkForValidMStickSize() {
        if (!validMStickSize()){
            throw new MorphException("MStick size check failed");
        }
    }

    protected void checkForTubeCollisions() {
        if (finalTubeCollisionCheck()){
            throw new MorphException("Tube collision check failed");
        }
    }

    private void attemptMutateRadius(int id, ComponentMorphParameters morphParams) {
        int numAttempts = 0;
        RadiusProfile oldRadiusProfile = retrieveOldRadiusProfile(id);
        while(numAttempts < NUM_ATTEMPTS_PER_RADIUS_PROFILE){
            try {
                mutateRadiusProfile(id, morphParams, oldRadiusProfile);
                applyRadiusProfile();
                return;
            } catch (MorphException e){
                System.err.println(e.getMessage());
            } finally {
                numAttempts++;
            }
        }
        if (numAttempts >= NUM_ATTEMPTS_PER_RADIUS_PROFILE){
            throw new MorphException("Failed to generate valid radius for using a morphed component " + id + " after " + NUM_ATTEMPTS_PER_RADIUS_PROFILE + " attempts.");
        }
    }

    protected void applyRadiusProfile() throws MorphException{
        for (int i=1; i<=getnComponent(); i++)
        {
            if(!getComp()[i].RadApplied_Factory()) // a fail application
            {
                throw new MorphException("Radius profile failed when attempting to be applied to component " + i);
            }
        }
//        if (getComp()[id].RadApplied_Factory() == false){
//            throw new MorphException("Radius profile failed when attempting to be applied to component " + id);
//        }
    }

    private void mutateRadiusProfile(int id, ComponentMorphParameters morphParams, RadiusProfile oldRadiusProfile) {
        RadiusProfile newRadiusProfile = morphParams.morphRadius(oldRadiusProfile);
        updateRadiusProfile(id, newRadiusProfile);
    }

    protected void updateRadiusProfile(int id, RadiusProfile newRadiusProfile) {
        // Update Junctions
        forEachJunctionThatContainsComp(id, new BiConsumer<JuncPt_struct, Integer>() {
            @Override
            public void accept(JuncPt_struct junction, Integer compIndx) {
                int uNdx = junction.getuNdx()[compIndx];
                if (newRadiusProfile.getInfoForRadius().containsKey(uNdx)) {
                    RadiusInfo radiusInfo = newRadiusProfile.getRadiusInfo(uNdx);
                    Double newRadius;
                    newRadius = radiusInfo.getRadius();

                    junction.setRad(newRadius);

                    for (int i=1; i<=junction.getnComp(); i++) {
                        uNdx = junction.getuNdx()[i];
                        double uValue = (uNdx - 1.0) / (51.0 - 1.0);
                        if (Math.abs(uValue - 0.0) < 0.0001) {
                            getComp()[junction.getCompIds()[i]].getRadInfo()[0][0] = 0.0;
                            getComp()[junction.getCompIds()[i]].getRadInfo()[0][1] = newRadius;
                        } else if (Math.abs(uValue - 1.0) < 0.0001) {
                            getComp()[junction.getCompIds()[i]].getRadInfo()[2][0] = 1.0;
                            getComp()[junction.getCompIds()[i]].getRadInfo()[2][1] = newRadius;
                        } else // middle u value
                        {
                            getComp()[junction.getCompIds()[i]].getRadInfo()[1][0] = uValue;
                            getComp()[junction.getCompIds()[i]].getRadInfo()[1][1] = newRadius;
                        }
                    }
                }
            }
        });


        // Update EndPts
        forEachEndPtOfComp(id, new Consumer<EndPt_struct>() {
            @Override
            public void accept(EndPt_struct endPt) {
                int uNdx = endPt.getuNdx();
                if (newRadiusProfile.getInfoForRadius().containsKey(uNdx)){
                    RadiusInfo radiusInfo = newRadiusProfile.getRadiusInfo(uNdx);
                    Double newRadius = radiusInfo.getRadius();

                    endPt.setRad(newRadius);
                    double uValue = (uNdx-1.0) / (51.0-1.0);
                    if ( Math.abs( uValue - 0.0) < 0.0001)
                    {
                        getComp()[id].getRadInfo()[0][0] = 0.0;
                        getComp()[id].getRadInfo()[0][1] = newRadius;
                    }
                    else if (Math.abs(uValue - 1.0) < 0.0001)
                    {
                        getComp()[id].getRadInfo()[2][0] = 1.0;
                        getComp()[id].getRadInfo()[2][1] = newRadius;
                    }
                    else // middle u value
                        System.out.println("werid");
//                        throw new MorphException("EndPt uNdx is not 1 or 51. uNdx = " + uNdx);
                }
            }
        });

        // MidPt If it will be changed
        int midPtUNdx = getComp()[id].getmAxisInfo().getBranchPt();
        if (newRadiusProfile.getInfoForRadius().containsKey(midPtUNdx)){
            RadiusInfo radiusInfo = newRadiusProfile.getRadiusInfo(midPtUNdx);
            Double newRadius = radiusInfo.getRadius();

            double uValue = (midPtUNdx-1.0) / (51.0-1.0);
            getComp()[id].getRadInfo()[1][0] = uValue;
            getComp()[id].getRadInfo()[1][1] = newRadius;
        }

    }

    /**
     reAssign the junction radius value
     One of the last function call by mutate()
     */
    protected void MutateSUB_reAssignJunctionRadius()
    {
        double rad_Volatile = 0;
        double nowRad, u_value;
        boolean showDebug = false;
        int try_time = 0;
        if ( showDebug)
            System.out.println("In radius reassign at junction");
        boolean[] radChgFlg = new boolean[ getnComponent()+1];
        int i, j;
        MorphedMatchStick old_mStick = new MorphedMatchStick();
        old_mStick.copyFrom(this); // a back up

        while (true)
        {
            // for all juncPt, we check the radius value is in the legal range,
            // if not, we must reassign,
            // if yes, there is certain probability we chg the assigned value
            for (i=1; i<= getnJuncPt(); i++)
            {

                double rMin = -10.0, rMax = 100000.0, tempX;
                int nRelated_comp = getJuncPt()[i].getnComp();
                for (j = 1 ; j <= nRelated_comp; j++)
                {
                    rMin = Math.max( rMin, getComp()[getJuncPt()[i].getCompIds()[j]].getmAxisInfo().getArcLen() / 10.0);
                    tempX = Math.min( 0.5 *getComp()[getJuncPt()[i].getCompIds()[j]].getmAxisInfo().getRad(),
                            getComp()[getJuncPt()[i].getCompIds()[j]].getmAxisInfo().getArcLen() / 3.0);
                    rMax = Math.min( rMax, tempX);
                }

                if (rMax < rMin)
                    System.out.println(" In radius assign, ERROR: rMax < rMin");

                boolean haveChg = false;
                nowRad = -10.0;
                // Check now Junc.rad versus rMin, rMax
                if ( getJuncPt()[i].getRad() > rMax || getJuncPt()[i].getRad() < rMin)
                {
                    haveChg = true; // definitely need to chg
                    if (stickMath_lib.rand01() < rad_Volatile)
                        nowRad = stickMath_lib.randDouble( rMin, rMax);
                    else // we don't want huge chg
                    {
                        if ( getJuncPt()[i].getRad() > rMax)  nowRad = rMax;
                        if ( getJuncPt()[i].getRad() < rMin)  nowRad = rMin;
                    }
                }
                else // the original value is in legal range
                {
                    if (stickMath_lib.rand01() < rad_Volatile)
                    {
                        haveChg = true;
                        while(true)
                        {
                            nowRad = stickMath_lib.randDouble( rMin, rMax);
                            double dist = Math.abs( nowRad - getJuncPt()[i].getRad());
                            double range = rMax - rMin;
                            if ( dist >= 0.2 * range) break; // not very near the original value
                        }
                    }

                }

                // set the new value to each component
                if ( haveChg ) // the radius have been chged
                {
                    getJuncPt()[i].setRad(nowRad);
                    for (j = 1 ; j <= nRelated_comp ; j++)
                    {
                        radChgFlg[ getJuncPt()[i].getCompIds()[j]] = true;
                        u_value = ((double)getJuncPt()[i].getuNdx()[j]-1.0) / (51.0-1.0);
                        if ( Math.abs( u_value - 0.0) < 0.0001)
                        {
                            getComp()[getJuncPt()[i].getCompIds()[j]].getRadInfo()[0][0] = 0.0;
                            getComp()[getJuncPt()[i].getCompIds()[j]].getRadInfo()[0][1] = nowRad;
                        }
                        else if ( Math.abs(u_value - 1.0) < 0.0001)
                        {
                            getComp()[getJuncPt()[i].getCompIds()[j]].getRadInfo()[2][0] = 1.0;
                            getComp()[getJuncPt()[i].getCompIds()[j]].getRadInfo()[2][1] = nowRad;
                        }
                        else // middle u value
                        {
                            getComp()[getJuncPt()[i].getCompIds()[j]].getRadInfo()[1][0] = u_value;
                            getComp()[getJuncPt()[i].getCompIds()[j]].getRadInfo()[1][1] = nowRad;
                        }
                    }
                }
            } // for loop along JuncPt

            // now use new radius value to generate new tube
            boolean success = true;
            for (i=1; i<= getnComponent(); i++)
                if ( radChgFlg[i] == true)
                {
                    if ( getComp()[i].RadApplied_Factory() == false)
                        success = false; // fail Jacob or gradR
                }
            if (success ) // then check closeHit & IntheBox
            {
                if ( this.validMStickSize() ==  false)
                    success = false;
                if ( this.finalTubeCollisionCheck() == true)
                    success = false;
            }

            if ( success )
                break; // not error, good
            else
            {
                //                System.out.println("In rad reassign at junction: need re-try");
                this.copyFrom(old_mStick);
                for (i=1; i<=getnComponent(); i++)
                    radChgFlg[i] = false;
                try_time++;
            }
            if ( try_time > 30)
                break; //give up the junction change
        } // while loop
    }

    public RadiusProfile retrieveOldRadiusProfile(int id) {
        double[][] old_radInfo = new double[3][2];
        for (int i=0; i<3; i++)
            for (int j=0; j<2; j++) {
                old_radInfo[i][j] = getComp()[id].getRadInfo()[i][j];
            }
        RadiusProfile oldRadiusProfile = new RadiusProfile();

        // Get old radius profile for this component;
        // Retrieve Radii from Junctions
        forEachJunctionThatContainsComp(id, new BiConsumer<JuncPt_struct, Integer>() {
            @Override
            public void accept(JuncPt_struct junction, Integer compIndx) {
                int uNdx = junction.getuNdx()[compIndx];
                Double oldRadius = junction.getRad();
                RadiusInfo junctionRadiusInfo = new RadiusInfo(oldRadius, uNdx, RADIUS_TYPE.JUNCTION, false);


                // Only add junction radius info if
                // the junction does not contain any components that should be preserved
                boolean junctionContainsPreservedComponents = false;
                for (int i=1; i<=junction.getnComp(); i++) {
                    if (compsToPreserve.contains(junction.getCompIds()[i])){
                        junctionContainsPreservedComponents = true;
                        break;
                    }
                }
                if (!preserveJunction){
                    oldRadiusProfile.addRadiusInfo(uNdx, junctionRadiusInfo);
                }
                else {
                    if (!junctionContainsPreservedComponents) {
                        oldRadiusProfile.addRadiusInfo(uNdx, junctionRadiusInfo);
                    }
                }
            }
        });

        // Retrieve Radii from EndPts
        forEachEndPtOfComp(id, new Consumer<EndPt_struct>() {
            @Override
            public void accept(EndPt_struct endPt) {
                int uNdx = endPt.getuNdx();
                Double oldRadius = endPt.getRad();
                RadiusInfo endPtRadiusInfo = new RadiusInfo(oldRadius, uNdx, RADIUS_TYPE.ENDPT, false);
                oldRadiusProfile.addRadiusInfo(uNdx, endPtRadiusInfo);
            }
        });

        // Retrieve Radius from MidPt
        int uNdx = getComp()[id].getmAxisInfo().getBranchPt();
        Double oldRadius = old_radInfo[1][1];
        RadiusInfo midPtRadiusInfo = new RadiusInfo(oldRadius, uNdx, RADIUS_TYPE.MIDPT, false);
        oldRadiusProfile.addRadiusInfo(uNdx, midPtRadiusInfo);
        return oldRadiusProfile;
    }

    protected void updateEndPtsAndJunctionPositions() {
        for (int i=1; i<=getnEndPt(); i++)
        {
            Point3d newPos = new Point3d(  getComp()[ getEndPt()[i].getComp()].getmAxisInfo().getmPts()[ getEndPt()[i].getuNdx()]);
            getEndPt()[i].getPos().set(newPos);

            Vector3d newTangent = new Vector3d( getComp()[ getEndPt()[i].getComp()].getmAxisInfo().getmTangent()[ getEndPt()[i].getuNdx()]);
            int in_undx = getEndPt()[i].getuNdx();
            if (in_undx == 51)
                newTangent.negate();
            getEndPt()[i].setTangent(newTangent);
        }
        for (int i=1; i<=getnJuncPt(); i++)
        {
            Point3d newPos = new Point3d( getComp()[getJuncPt()[i].getCompIds()[1]].getmAxisInfo().getmPts()[ getJuncPt()[i].getuNdx()[1]]);
            getJuncPt()[i].getPos().set(newPos);
        }
    }

    protected void checkForCollisions(int id) throws MorphException{
        boolean closeHit = checkSkeletonNearby(getNComponent());
        if (closeHit){
            throw new MorphException("Skeleton Collision Check Failed");
        }
    }

    protected void updateJuncPtsForNewComp(int id) {
        forEachJunctionThatContainsComp(id, new BiConsumer<JuncPt_struct, Integer>() {
            @Override
            public void accept(JuncPt_struct junction, Integer jIndex) {
                int nowUNdx = junction.getuNdx()[jIndex];
                Vector3d finalTangent = new Vector3d(newArc.getmTangent()[nowUNdx]);
                if (nowUNdx == 51)
                    finalTangent.negate();
                Point3d newPos = new Point3d(newArc.getmPts()[nowUNdx]);
                //Define shiftVec as distance between new position and the current incorrect junction position
                Point3d shiftVec = new Point3d();
                shiftVec.sub(newPos, junction.getPos());

                // For each component attached to this junction if it's not the alignedPT
                // Translate it to its final position
//                if(true) {
                if(nowUNdx != newArc.getTransRotHis_alignedPt()){
                    for (int j=1; j<=junction.getnComp(); j++){
                        int nowCompIndex = junction.getCompIds()[j];
                        if ( nowCompIndex != id){
                            for (int k=1; k<=getnComponent(); k++){
                                if (compLabel[k] == nowCompIndex) {
                                    AllenTubeComp attachedComp = getComp()[k];
                                    Point3d finalPos = new Point3d();
                                    finalPos.add(attachedComp.getmAxisInfo().getTransRotHis_finalPos(), shiftVec);
                                    attachedComp.translateComp(newPos);
                                }
                            }
                        }
                    }
                }

                //Set the new position of the junction
                junction.setPos(newPos);
                junction.getTangent()[jIndex].set(finalTangent);
//                // Set the new tangent of the junction
//                boolean secondFlg = false; // determine if the first or second tangent
//                for ( int j = 1; j <= junction.getnTangent(); j++)
//                {
//                    if (junction.getTangentOwner()[j] == id && secondFlg == false)
//                    {
//                        junction.getTangent()[j].set(finalTangent);
//                        secondFlg = true;
//                    }
//                    else if ( junction.getTangentOwner()[j] == id && secondFlg == true)
//                    {
//                        finalTangent.negate();
//                        junction.getTangent()[j].set(finalTangent);
//                    }
//                }
            }
        });
    }

    private AllenMAxisArc attemptToGenerateValidMorphedArc(int id, ComponentMorphParameters morphParams) {
        MorphedMAxisArc arcToMorph = new MorphedMAxisArc(getComp()[id].getmAxisInfo());
        int numAttemptsToGenerateArc = 0;
        while(numAttemptsToGenerateArc < NUM_ATTEMPTS_PER_ARC){
            try {
                newArc = generateMorphedArc(id, morphParams, arcToMorph);
                checkJunctions(id, newArc); //not sure needed because this just checks diff betwene new and old
                return newArc;
            } catch (MorphException e){
                System.err.println(e.getMessage());
                System.out.println("Failed to generate a valid morphed arc.");
                System.out.println("Retrying generate a valid morphed arc");
//                this.copyFrom(localBackup);
            } finally {
                numAttemptsToGenerateArc++;
            }
        }
        throw new MorphException("Failed to generate a valid morphed arc after " + NUM_ATTEMPTS_PER_ARC + " attempts.");

    }

    protected void checkJunctions(int id, AllenMAxisArc newArc) throws MorphException{
        forEachJunctionThatContainsComp(id, new BiConsumer<JuncPt_struct, Integer>() {
            @Override
            public void accept(JuncPt_struct junction, Integer compIndx) {
                int nowUNdx = junction.getuNdx()[compIndx];
                int alignedPt = newArc.getTransRotHis_alignedPt();

                Vector3d finalTangent;
                boolean midBranchFlg = false;
                finalTangent = new Vector3d(newArc.getmTangent()[nowUNdx]);
                if (nowUNdx == 1) {
                    //do nothing
                }
                else if (nowUNdx == 51){
                    finalTangent.negate();
                }
                else{
                    midBranchFlg = true;
                }

//                // check the angle
//                for (int j=1; j<=junction.getnTangent(); j++) {
//                    if (junction.getTangentOwner()[j] != id) // don't need to check with the replaced self
//                    {
//                        Vector3d nowTangent = junction.getTangent()[j]; // soft copy is fine here
//                        if (nowTangent.angle(finalTangent) <= getTangentSaveZone()) // angle btw the two tangent vector
//                            throw new MorphException("Tangent angle too small!");
//                        if (midBranchFlg == true) {
//                            finalTangent.negate();
//                            if (nowTangent.angle(finalTangent) <= getTangentSaveZone()) //
//                                throw new MorphException("Tangent angle too small!");
//                        }
//                    }
//                }
            }
        });
    }

    private MorphedMAxisArc generateMorphedArc(int id, ComponentMorphParameters morphParams, MorphedMAxisArc arcToMorph) {
        int alignedPt = MutationSUB_determineHinge(id);
//        int alignedPt = arcToMorph.getTransRotHis_alignedPt();
        MorphedMAxisArc newArc = new MorphedMAxisArc();
        newArc.genMorphedArc(arcToMorph, alignedPt, morphParams);
        return newArc;
    }

    protected void forEachJunctionThatContainsComp(int id, BiConsumer<JuncPt_struct, Integer> junctionCompIdConsumer) {
        for (int i = 1; i<= getnJuncPt(); i++) {
            for (int j = 1; j <= getJuncPt()[i].getnComp(); j++){
                if (getJuncPt()[i].getCompIds()[j] == id) {
                    junctionCompIdConsumer.accept(getJuncPt()[i], j);
                }
            }
        }
    }

    private void forEachEndPtOfComp(int id, Consumer<EndPt_struct> endPtConsumer) {
        for (int i=1; i<=getnEndPt(); i++){
            if (getEndPt()[i].getComp() == id) {
                endPtConsumer.accept(getEndPt()[i]);
            }
        }
    }

    @Override
    public void copyFrom(AllenMatchStick in) {
        super.copyFrom(in);

        if (in instanceof MorphedMatchStick){
            this.setMorphData(new MorphData(((MorphedMatchStick) in).getMorphData()));
        }
    }

    @Override
    protected void cleanData()
    {
        super.cleanData();

        if (getMorphData() != null){
            setMorphData(new MorphData());
        }
    }

    @Override
    public double getTangentSaveZone() {
        return TangentSaveZone;
    }

    @Override
    public void setTangentSaveZone(double tangentSaveZone) {
        TangentSaveZone = tangentSaveZone;
    }

    public MorphData getMorphData() {
        return morphData;
    }

    public void setMorphData(MorphData morphData) {
        this.morphData = morphData;
    }

    public static class MorphException extends RuntimeException{
        public MorphException(String message){
            super(message);
        }
    }

    @Override
    public double[] getPARAM_nCompDist() {
        return PARAM_nCompDist;
    }

    @Override
    public double getPROB_addTiptoBranch() {
        return PROB_addTiptoBranch;
    }

    @Override
    public double getPROB_addToEndorJunc() {
        return PROB_addToEndorJunc;
    }

    @Override
    public double getPROB_addToEnd_notJunc() {
        return PROB_addToEnd_notJunc;
    }

    public int getMaxTotalAttempts() {
        return MAX_TOTAL_ATTEMPTS;
    }

    public void setMaxTotalAttempts(int maxTotalAttempts) {
        MAX_TOTAL_ATTEMPTS = maxTotalAttempts;
    }

    public static class MStickSizeException extends MorphException{
        public MStickSizeException(String message){
            super(message);
        }
    }
}