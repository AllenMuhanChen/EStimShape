package org.xper.allen.drawing.composition;

import org.xper.allen.drawing.composition.morph.ComponentMorphParameters;
import org.xper.allen.drawing.composition.morph.ComponentMorphParameters.RadiusInfo;
import org.xper.allen.drawing.composition.morph.ComponentMorphParameters.RadiusProfile;
import org.xper.allen.drawing.composition.morph.MorphedMAxisArc;
import org.xper.drawing.stick.EndPt_struct;
import org.xper.drawing.stick.JuncPt_struct;
import org.xper.drawing.stick.MatchStick;
import org.xper.drawing.stick.stickMath_lib;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;
import java.util.Map;
import java.util.function.BiConsumer;
import java.util.function.Consumer;

public class MorphedMatchStick extends AllenMatchStick{
    private static final int NUM_ATTEMPTS_PER_COMPONENT = 5;
    private static final int NUM_ATTEMPTS_PER_SKELETON = 5;
    private static final int NUM_ATTEMPTS_PER_ARC = 100;
    private static final double NUM_ATTEMPTS_PER_RADIUS_PROFILE = 5;
    private MorphedMAxisArc newArc;
    private int[] compLabel;

    public void genMorphedMatchStick(Map<Integer, ComponentMorphParameters> morphParametersForComponents, MorphedMatchStick matchStickToMorph){
        MorphedMatchStick backup = new MorphedMatchStick();
        backup.copyFrom(matchStickToMorph);
        copyFrom(backup);

        // Attempt to morph every component. If we fail, then restart with the backup.
        while (true) {
            try {
                morphAllComponents(morphParametersForComponents, matchStickToMorph);
                MutateSUB_reAssignJunctionRadius();
                positionShape();
                attemptSmoothizeMStick();
                return;
            } catch (MorphException e) {
                cleanData();
                copyFrom(backup);
                e.printStackTrace();
                System.err.println("Failed to morph matchstick. Retrying...");
            }
        }
    }

    private void morphAllComponents(Map<Integer, ComponentMorphParameters> morphParametersForComponents, MorphedMatchStick matchStickToMorph) {
        morphParametersForComponents.forEach(new BiConsumer<Integer, ComponentMorphParameters>() {
            @Override
            public void accept(Integer componentIndex, ComponentMorphParameters morphParams) {
                attemptToMorphComponent(componentIndex, morphParams, matchStickToMorph);
            }
        });
    }

    /**
     * Makes several attempts to morph a single component given a set of morph parameters.
     * If any attempt fails, it will load a backup of the matchstick and try again.
     * If all attempts fail, it will throw a MorphException.

     */
    private void attemptToMorphComponent(Integer componentIndex, ComponentMorphParameters morphParams, MorphedMatchStick matchStickToMorph) {
        MorphedMatchStick localBackup = new MorphedMatchStick();
        localBackup.copyFrom(matchStickToMorph);

        int numAttempts=0;
        while (numAttempts < NUM_ATTEMPTS_PER_COMPONENT) {
            try {
                morphComponent(componentIndex, morphParams);
                System.out.println("Successfully morphed component " + componentIndex);
                return;
            } catch (MorphException e) {
                e.printStackTrace();
                System.err.println("Failed to Morph Component " + componentIndex + " with parameters " + morphParams);
                System.err.println("Retrying...");
                System.err.println("Attempt " + numAttempts + " of " + NUM_ATTEMPTS_PER_COMPONENT);
                matchStickToMorph.copyFrom(localBackup);
                morphParams.redistribute();
            } finally {
                numAttempts++;
            }
        }
        throw new MorphException("Did not successfully morph component " + componentIndex + " after " + NUM_ATTEMPTS_PER_COMPONENT + " attempts.");
    }

    private void morphComponent(int id, ComponentMorphParameters morphParams) throws MorphException{
        compLabel = MutationSUB_compRelation2Target(id);

        attemptToGenerateValidComponentSkeleton(id, morphParams);
        updateEndPtsAndJunctions();

        attemptMutateRadius(id, morphParams);

        checkForTubeCollisions();
        checkForValidMStickSize();


    }

    private void attemptToGenerateValidComponentSkeleton(int id, ComponentMorphParameters morphParams) {
        MorphedMatchStick backUp = new MorphedMatchStick();
        backUp.copyFrom(this);
        int numAttempts = 0;
        while(numAttempts < NUM_ATTEMPTS_PER_SKELETON){
            try {
                newArc = attemptToGenerateValidMorphedArc(id, morphParams);
                updateJuncPtsForNewComp(id);
                updateComponentInfo(id);
                checkForCollisions(id);
                System.out.println("Successfully generated valid skeleton for component " + id);
                return;
            } catch (MorphException e){
                copyFrom(backUp);
                e.printStackTrace();
                System.out.println("FAILED Attempt " + numAttempts + " of " + NUM_ATTEMPTS_PER_SKELETON + " to generate valid skeleton for component " + id);
            } finally {
                numAttempts++;

            }
        }
        throw new MorphException("Failed to generate valid skeleton for using a morphed component " + id + " after " + NUM_ATTEMPTS_PER_SKELETON + " attempts.");
    }

    private void updateComponentInfo(int id) {
        boolean branchUsed = getComp()[id].isBranchUsed();
        int connectType = getComp()[id].getConnectType();
        double[][] oldRadInfo = getComp()[id].getRadInfo();

        addTube(id);
        getComp()[id].setRadInfo(oldRadInfo);
        getComp()[id].getmAxisInfo().copyFrom(newArc);
        getComp()[id].setBranchUsed(branchUsed);
        getComp()[id].setConnectType(connectType);
    }

    private void attemptSmoothizeMStick() {
        boolean success = false;
        if(!success){
            boolean res;
            try{
                res = smoothizeMStick();
            } catch(Exception e){
                throw new MorphException("Failed to smoothize the matchstick!");
            }
            if(!res){
                throw new MorphException("Failed to smoothize the matchstick!");
            }
        }
    }

    private void checkForValidMStickSize() {
        if (!validMStickSize()){
            throw new MorphException("MStick size check failed");
        }
    }

    private void checkForTubeCollisions() {
        if (finalTubeCollisionCheck()){
            throw new MorphException("Tube collision check failed");
        }
    }

    private void attemptMutateRadius(int id, ComponentMorphParameters morphParams) {
        int numAttempts = 0;
        RadiusProfile oldRadiusProfile = retrieveOldRadiusProfile(id);
        MorphedMatchStick backup = new MorphedMatchStick();
        backup.copyFrom(this);
        while(numAttempts < NUM_ATTEMPTS_PER_RADIUS_PROFILE){
            try {
                mutateRadiusProfile(id, morphParams, oldRadiusProfile);
                applyRadiusProfile(id);
                System.out.println("Successfully generated valid radius for component " + id);
                return;
            } catch (MorphException e){
                copyFrom(backup);
                e.printStackTrace();
            } finally {
                numAttempts++;
            }
        }
        if (numAttempts >= NUM_ATTEMPTS_PER_RADIUS_PROFILE){
            throw new MorphException("Failed to generate valid radius for using a morphed component " + id + " after " + NUM_ATTEMPTS_PER_ARC + " attempts.");
        }
    }

    private void applyRadiusProfile(int id) throws MorphException{
        if (getComp()[id].RadApplied_Factory() == false){
            throw new MorphException("Radius profile failed when attempting to be applied to component " + id);
        }
    }

    private void mutateRadiusProfile(int id, ComponentMorphParameters morphParams, RadiusProfile oldRadiusProfile) {
        RadiusProfile newRadiusProfile = morphParams.getRadius(oldRadiusProfile);
        updateRadiusProfile(id, newRadiusProfile);
    }

    private void updateRadiusProfile(int id, RadiusProfile newRadiusProfile) {
        // Update Junctions
        forEachJunctionThatContainsComp(id, new BiConsumer<JuncPt_struct, Integer>() {
            @Override
            public void accept(JuncPt_struct junction, Integer compIndx) {
                int uNdx = junction.getuNdx()[compIndx];
                if (newRadiusProfile.getInfoForRadius().containsKey(uNdx)) {
                    RadiusInfo radiusInfo = newRadiusProfile.getRadiusInfo(uNdx);
                    Double newRadius = radiusInfo.getRadius();

                    junction.setRad(newRadius);

                    for (int i=1; i<=junction.getnComp(); i++) {
                        uNdx = junction.getuNdx()[i];
                        double uValue = (uNdx - 1.0) / (51.0 - 1.0);
                        if (Math.abs(uValue - 0.0) < 0.0001) {
                            getComp()[junction.getComp()[i]].getRadInfo()[0][0] = 0.0;
                            getComp()[junction.getComp()[i]].getRadInfo()[0][1] = newRadius;
                        } else if (Math.abs(uValue - 1.0) < 0.0001) {
                            getComp()[junction.getComp()[i]].getRadInfo()[2][0] = 1.0;
                            getComp()[junction.getComp()[i]].getRadInfo()[2][1] = newRadius;
                        } else // middle u value
                        {
                            getComp()[junction.getComp()[i]].getRadInfo()[1][0] = uValue;
                            getComp()[junction.getComp()[i]].getRadInfo()[1][1] = newRadius;
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
                        throw new MorphException("EndPt uNdx is not 1 or 51. uNdx = " + uNdx);
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
        MatchStick old_mStick = new MatchStick();
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
                    rMin = Math.max( rMin, getComp()[getJuncPt()[i].getComp()[j]].getmAxisInfo().getArcLen() / 10.0);
                    tempX = Math.min( 0.5 *getComp()[getJuncPt()[i].getComp()[j]].getmAxisInfo().getRad(),
                            getComp()[getJuncPt()[i].getComp()[j]].getmAxisInfo().getArcLen() / 3.0);
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
                        radChgFlg[ getJuncPt()[i].getComp()[j]] = true;
                        u_value = ((double)getJuncPt()[i].getuNdx()[j]-1.0) / (51.0-1.0);
                        if ( Math.abs( u_value - 0.0) < 0.0001)
                        {
                            getComp()[getJuncPt()[i].getComp()[j]].getRadInfo()[0][0] = 0.0;
                            getComp()[getJuncPt()[i].getComp()[j]].getRadInfo()[0][1] = nowRad;
                        }
                        else if ( Math.abs(u_value - 1.0) < 0.0001)
                        {
                            getComp()[getJuncPt()[i].getComp()[j]].getRadInfo()[2][0] = 1.0;
                            getComp()[getJuncPt()[i].getComp()[j]].getRadInfo()[2][1] = nowRad;
                        }
                        else // middle u value
                        {
                            getComp()[getJuncPt()[i].getComp()[j]].getRadInfo()[1][0] = u_value;
                            getComp()[getJuncPt()[i].getComp()[j]].getRadInfo()[1][1] = nowRad;
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

    private RadiusProfile retrieveOldRadiusProfile(int id) {
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
                RadiusInfo junctionRadiusInfo = new RadiusInfo(oldRadius, uNdx, ComponentMorphParameters.RADIUS_TYPE.JUNCTION, false);
                oldRadiusProfile.addRadiusInfo(uNdx, junctionRadiusInfo);
            }
        });

        // Retrieve Radii from EndPts
        forEachEndPtOfComp(id, new Consumer<EndPt_struct>() {
            @Override
            public void accept(EndPt_struct endPt) {
                int uNdx = endPt.getuNdx();
                Double oldRadius = endPt.getRad();
                RadiusInfo endPtRadiusInfo = new RadiusInfo(oldRadius, uNdx, ComponentMorphParameters.RADIUS_TYPE.ENDPT, false);
                oldRadiusProfile.addRadiusInfo(uNdx, endPtRadiusInfo);
            }
        });

        // Retrieve Radius from MidPt
        int uNdx = getComp()[id].getmAxisInfo().getBranchPt();
        Double oldRadius = old_radInfo[1][1];
        RadiusInfo midPtRadiusInfo = new RadiusInfo(oldRadius, uNdx, ComponentMorphParameters.RADIUS_TYPE.MIDPT, false);
        oldRadiusProfile.addRadiusInfo(uNdx, midPtRadiusInfo);
        return oldRadiusProfile;
    }

    private void updateEndPtsAndJunctions() {
        for (int i=1; i<=getnEndPt(); i++)
        {
            Point3d newPos = new Point3d(  getComp()[ getEndPt()[i].getComp()].getmAxisInfo().getmPts()[ getEndPt()[i].getuNdx()]);
            getEndPt()[i].getPos().set(newPos);
        }
        for (int i=1; i<=getnJuncPt(); i++)
        {
            Point3d newPos = new Point3d( getComp()[getJuncPt()[i].getComp()[1]].getmAxisInfo().getmPts()[ getJuncPt()[i].getuNdx()[1]]);
            getJuncPt()[i].getPos().set(newPos);
        }
    }

    private void checkForCollisions(int id) throws MorphException{
        boolean closeHit = checkSkeletonNearby(getNComponent());
        if (closeHit){
            throw new MorphException("Skeleton nearby");
        }
    }

    private void updateJuncPtsForNewComp(int id) {
        forEachJunctionThatContainsComp(id, new BiConsumer<JuncPt_struct, Integer>() {
            @Override
            public void accept(JuncPt_struct junction, Integer compIndx) {
                int nowUNdx = junction.getuNdx()[compIndx];
                Vector3d finalTangent = newArc.getmTangent()[nowUNdx];
                Point3d newPos = newArc.getmPts()[nowUNdx];
                Point3d shiftVec = new Point3d();
                shiftVec.sub(newPos, junction.getPos());

                // For each component attached to this junction if it's not the alignedPT
                // Translate it to its final position
                if(nowUNdx != newArc.getTransRotHis_alignedPt()){
                    for (int j=1; j<=junction.getnComp(); j++){
                        int nowCompIndex = junction.getComp()[j];
                        if ( nowCompIndex != id){
                            for (int k=1; k<=getnComponent(); k++){
                                if (compLabel[k] == nowCompIndex) {
                                    AllenTubeComp attachedComp = getComp()[k];
                                    Point3d finalPos = attachedComp.getmAxisInfo().getTransRotHis_finalPos();
                                    finalPos.add(shiftVec);
                                    attachedComp.translateComp(finalPos);
                                }
                            }
                        }
                    }
                }

                //Set the new position of the junction
                junction.setPos(newPos);

                // Set the new tangent of the junction
                boolean secondFlg = false; // determine if the first or second tangent
                for ( int j = 1; j <= junction.getnTangent(); j++)
                {
                    if (junction.getTangentOwner()[j] == id && secondFlg == false)
                    {
                        junction.getTangent()[j].set(finalTangent);
                        secondFlg = true;
                    }
                    else if ( junction.getTangentOwner()[j] == id && secondFlg == true)
                    {
                        finalTangent.negate();
                        junction.getTangent()[j].set(finalTangent);
                    }
                }
            }
        });
    }

    private MorphedMAxisArc attemptToGenerateValidMorphedArc(int id, ComponentMorphParameters morphParams) {
        MorphedMatchStick backup = new MorphedMatchStick();
        backup.copyFrom(this);

        MorphedMAxisArc arcToMorph = new MorphedMAxisArc(getComp()[id].getmAxisInfo());
        int numAttemptsToGenerateArc = 0;
        while(numAttemptsToGenerateArc < NUM_ATTEMPTS_PER_ARC){
            try {
                newArc = generateMorphedArc(id, morphParams, arcToMorph);
                checkJunctions(id, newArc);
                return newArc;
            } catch (MorphException e){
                copyFrom(backup);
                System.err.println("Failed to generate a valid morphed arc. Attempting again...");
                e.printStackTrace();
            } finally {
                numAttemptsToGenerateArc++;
            }
        }
        throw new MorphException("Failed to generate a valid morphed arc after " + NUM_ATTEMPTS_PER_COMPONENT + " attempts.");

    }

    private void checkJunctions(int id, MorphedMAxisArc newArc) throws MorphException{
        forEachJunctionThatContainsComp(id, new BiConsumer<JuncPt_struct, Integer>() {
            @Override
            public void accept(JuncPt_struct junction, Integer compIndx) {
                int nowUNdx = junction.getuNdx()[compIndx];
                int alignedPt = newArc.getTransRotHis_alignedPt();

                Vector3d finalTangent;
                boolean midBranchFlg = false;
                finalTangent = newArc.getmTangent()[nowUNdx];
                if (nowUNdx == 1) {
                    //do nothing
                }
                else if (nowUNdx == 51){
                    finalTangent.negate();
                }
                else{
                    midBranchFlg = true;
                }

                // check the angle
                for (int j=1; j<=junction.getnTangent(); j++) {
                    if (junction.getTangentOwner()[j] != id) // don't need to check with the replaced self
                    {
                        Vector3d nowTangent = junction.getTangent()[j]; // soft copy is fine here
                        if (nowTangent.angle(finalTangent) <= getTangentSaveZone()) // angle btw the two tangent vector
                            throw new MorphException("Tangent angle too small!");
                        if (midBranchFlg == true) {
                            finalTangent.negate();
                            if (nowTangent.angle(finalTangent) <= getTangentSaveZone()) //
                                throw new MorphException("Tangent angle too small!");
                        }
                    }
                }
            }
        });
    }

    private MorphedMAxisArc generateMorphedArc(int id, ComponentMorphParameters morphParams, MorphedMAxisArc arcToMorph) {
        int alignedPt = MutationSUB_determineHinge(id);
        MorphedMAxisArc newArc = new MorphedMAxisArc();
        newArc.genMorphedArc(arcToMorph, alignedPt, morphParams);
        return newArc;
    }

    protected void forEachJunctionThatContainsComp(int id, BiConsumer<JuncPt_struct, Integer> junctionCompIdConsumer) {
        for (int i = 1; i<= getnJuncPt(); i++) {
            for (int j = 1; j <= getJuncPt()[i].getnComp(); j++){
                if (getJuncPt()[i].getComp()[j] == id) {
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

    public static class MorphException extends RuntimeException{
        public MorphException(String message){
            super(message);
        }
    }

}