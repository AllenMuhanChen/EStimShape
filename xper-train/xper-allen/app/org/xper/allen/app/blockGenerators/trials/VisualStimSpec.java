package org.xper.allen.app.blockGenerators.trials;

import org.xper.allen.specs.StimSpec;
import org.xper.drawing.Coordinates2D;

import com.thoughtworks.xstream.XStream;
import com.thoughtworks.xstream.annotations.XStreamAlias;

public class VisualStimSpec extends StimSpec{
	
	/**
	 * 
	 * @param targetEyeWinCoords
	 * @param targetEyeWinSize
	 * @param duration
	 * @param taskid
	 */
	public VisualStimSpec(Coordinates2D targetEyeWinCoords, double targetEyeWinSize, double duration, long taskid) {
		super();
		//Defaults
		this.eStimObjData = new long[] {1};
		this.eStimObjChans = new int[] {1};
		this.stimObjData = new long[] {taskid};
		//
		this.targetEyeWinCoords = targetEyeWinCoords;
		this.targetEyeWinSize = targetEyeWinSize;
		this.duration = duration;
		
		s = new XStream();
		s.alias("StimSpec", VisualStimSpec.class);
		s.setMode(XStream.NO_REFERENCES);
	}
	
	@Override
	public String toXml() {
		return s.toXML(this);
	}
}
