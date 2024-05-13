package org.xper.allen.drawing.composition.experiment;

import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.pga.RFStrategy;

/**
 * MatchSticks that are used to generate stimuli for the EStimShape NAFC Experiment.
 *
 * Includes:
 * 1. the ability to generate mSticks from base components and generate delta trials.
 * 2. partially or completely inside Receptive Field behavior based on special limb.
 *
 */
public class EStimShapeProceduralMatchStick extends ProceduralMatchStick {
    RFStrategy rfStrategy;
    ReceptiveField rf;


}