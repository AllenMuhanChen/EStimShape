package org.xper.allen.drawing.composition.ga;

import org.xper.allen.drawing.composition.AllenMatchStick;

public class GrowingMatchStick extends AllenMatchStick {


    public boolean mutate() {
        // Decide our mutations
            // Decide if we're going to add or remove limbs

            // Determines which limbs are leafs and which are not

            // Decides for each limb, whether to do nothing, replace whole, do a fine change, or remove it
            // Probability depends on whether the limb is a leaf or not (we shouldn't remove a center limb or completely replace it)

            // Checks if the number of changes that are occurring is not too big or small
            // IF everything is fine, we break out of the loop


        // Mutation Process Loop (If at any point, a mutation fails, we retry)
            // Make a backup of the specified changes

            // Removal mutations

            // Whole change mutations
            // Fine change mutations

            // Add mutations - local loop to try multiple times

            // Mutate junction radii

        // Post - Process

            // Check size of mstick

            // Change final rotation

            // Smoothize


        return false;
    }

    private boolean fineChangeComponent(int id) {
        // Find alignedPt - the point that is aligned with the junction point
        // Find the junction points associated with this limb

        // Generate a New Arc (why we need the alignedPt, it needs to start somewhere)

        // Check Arc
            // Calculate junction angles
        return false;
    }


}