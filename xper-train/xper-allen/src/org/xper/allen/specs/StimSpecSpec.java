package org.xper.allen.specs;

import org.xper.drawing.Coordinates2D;

import com.thoughtworks.xstream.XStream;
import com.thoughtworks.xstream.annotations.XStreamAlias;

/**
 * Fields correspond with xml entries in the "spec" column in "v1microstim.stimspec" database table. 
 * Contains toXML and fromXML methods. 
 * @author Allen Chen
 *
 */
public class StimSpecSpec {
	@XStreamAlias("targetEyeWinCoords")
	protected Coordinates2D targetEyeWinCoords;
	@XStreamAlias("targetEyeWinSize")
	protected double targetEyeWinSize;
	@XStreamAlias("duration")
	protected double duration;
	@XStreamAlias("stimObjData")
	protected long[] stimObjData;
	@XStreamAlias("eStimObjData")
	protected long[] eStimObjData;
	@XStreamAlias("eStimObjChans")
	protected int[] eStimObjChans;
	
	protected transient static XStream s;
	
	static {
		s = new XStream();
		s.alias("StimSpec", StimSpecSpec.class);
	}
	
	public StimSpecSpec(Coordinates2D targetEyeWinCoords, double targetEyeWinSize, double duration, long[] stimObjData,
			long[] eStimObjData, int[] eStimObjChans) {
		super();
		this.targetEyeWinCoords = targetEyeWinCoords;
		this.targetEyeWinSize = targetEyeWinSize;
		this.duration = duration;
		this.stimObjData = stimObjData;
		this.eStimObjData = eStimObjData;
		this.eStimObjChans = eStimObjChans;
	}

	
	public StimSpecSpec() {
	}


	public static String toXml (StimSpecSpec spec) {
		return s.toXML(spec);
	}
	
	public String toXml() {
		return StimSpecSpec.toXml(this);
	}
	
	public static StimSpecSpec fromXml (String xml) {
		StimSpecSpec ss = (StimSpecSpec)s.fromXML(xml);
		return ss;
	}

	public long[] getStimObjData() {
		return stimObjData;
	}

	public void setStimObjData(long[] stimObjData) {
		this.stimObjData = stimObjData;
	}

	public long[] geteStimObjData() {
		return eStimObjData;
	}

	public void seteStimObjData(long[] eStimObjData) {
		this.eStimObjData = eStimObjData;
	}

	public int[] geteStimObjChans() {
		return eStimObjChans;
	}

	public void seteStimObjChans(int[] eStimObjChans) {
		this.eStimObjChans = eStimObjChans;
	}

	public double getTargetEyeWinSize() {
		return targetEyeWinSize;
	}

	public void setTargetEyeWinSize(double targetEyeWinSize) {
		this.targetEyeWinSize = targetEyeWinSize;
	}

	public double getDuration() {
		return duration;
	}

	public void setDuration(double duration) {
		this.duration = duration;
	}

	public Coordinates2D getTargetEyeWinCoords() {
		return targetEyeWinCoords;
	}

	public void setTargetEyeWinCoords(Coordinates2D targetEyeWinCoords) {
		this.targetEyeWinCoords = targetEyeWinCoords;
	}

}
