package org.xper.allen.saccade.blockgen;

import org.xper.allen.saccade.db.vo.EStimObjDataEntry;
import org.xper.allen.specs.GaussSpec;
import org.xper.drawing.Coordinates2D;

import com.thoughtworks.xstream.XStream;

public class EStimTrial extends VEStimTrial implements Trial {

	
	transient XStream s = new XStream();
	
	public EStimTrial(EStimObjDataEntry eStimSpec, Coordinates2D targetEyeWinCoords, double targetEyeWinSize, double duration, String data) {
		super(eStimSpec, null, targetEyeWinCoords, targetEyeWinSize, duration, data);
		gaussSpec = catchGaussSpec();
	}
	
	public EStimTrial() {
		
	}
	
	private GaussSpec catchGaussSpec() {
		return new GaussSpec(0, 0, 0, 0);
		
	}
	
	public String toXml() {
		return s.toXML(this);
	}

}
