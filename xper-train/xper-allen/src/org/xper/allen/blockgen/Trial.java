package org.xper.allen.blockgen;

import org.xper.allen.db.vo.EStimObjDataEntry;
import org.xper.allen.specs.EStimObjData;
import org.xper.allen.specs.GaussSpec;
import org.xper.drawing.Coordinates2D;

/**
 * Interface for YourTrial, so all Trial types can be grouped together.
 * @author Allen Chen
 *
 */
public interface Trial {

	String toXml();

	GaussSpec getGaussSpec();

	EStimObjDataEntry getEStimSpec();

	Coordinates2D getTargetEyeWinCoords();

	double getTargetEyeWinSize();

	double getDuration();

	String getData();

}
