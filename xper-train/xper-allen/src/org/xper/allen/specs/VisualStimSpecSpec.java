package org.xper.allen.specs;

import org.xper.drawing.Coordinates2D;

import com.thoughtworks.xstream.XStream;
import com.thoughtworks.xstream.annotations.XStreamAlias;

/**
 * Fields correspond with xml entries of "spec" column of "v1microstim.stimspec database table"   
 * Contains toXML and from XML functions. 
 *
 * @param targetEyeWinCoords
 * @param targetEyeWinSize
 * @param duration
 * @param taskid
 * @author Allen Chen
 * 
 */
public class VisualStimSpecSpec extends SaccadeStimSpecSpec{
	

	
	public VisualStimSpecSpec(Coordinates2D targetEyeWinCoords, double targetEyeWinSize, double duration, long taskid) {
		super();
		//Defaults
		this.eStimObjData = new long[] {1};
		this.stimObjData = new long[] {taskid};
		//
		this.targetEyeWinCoords = targetEyeWinCoords;
		this.targetEyeWinSize = targetEyeWinSize;
		this.duration = duration;
		
		s = new XStream();
		s.alias("StimSpec", VisualStimSpecSpec.class);
		s.setMode(XStream.NO_REFERENCES);
	}
	
	@Override
	public String toXml() {
		return s.toXML(this);
	}
}
