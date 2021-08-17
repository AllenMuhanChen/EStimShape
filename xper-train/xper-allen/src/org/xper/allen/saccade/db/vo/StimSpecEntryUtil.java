package org.xper.allen.saccade.db.vo;

import org.xper.allen.specs.SaccadeStimSpecSpec;
import org.xper.allen.specs.NAFCStimSpecSpec;
import org.xper.db.vo.StimSpecEntry;

import com.thoughtworks.xstream.XStream;

/**
 * Provides methods that adds functionality to StimSpecs. Allows for XMLserializing and deserializing  
 * @author allenchen
 *
 */
public class StimSpecEntryUtil{

	
	StimSpecEntry stimSpecEntry;
	/**
	 * It's the timestamp in microseconds.
	 */
	long stimId;
	
	public StimSpecEntryUtil(StimSpecEntry sse) {
		this.stimSpecEntry = sse;
	}
	
	/**
	 * Transforms stimSpec xml String into StimSpecSpec object. 
	 * @return
	 */
	public SaccadeStimSpecSpec saccadeStimSpecSpecFromXmlSpec() {
		SaccadeStimSpecSpec ss = SaccadeStimSpecSpec.fromXml(stimSpecEntry.getSpec());
		return ss;
	}
	
	public NAFCStimSpecSpec twoACStimSpecSpecFromXmlSpec() {
		NAFCStimSpecSpec ss = NAFCStimSpecSpec.fromXml(stimSpecEntry.getSpec());
		return ss;
	}
	
	
	transient static XStream s;

	static {
		s = new XStream();
		s.alias("StimSpec", StimSpecEntry.class);
	}

	public String toXml() {
		return s.toXML(stimSpecEntry);
	}

	public static StimSpecEntry fromXml(String xml) {
		StimSpecEntry g = (StimSpecEntry) s.fromXML(xml);
		return g;
	}
	

}
