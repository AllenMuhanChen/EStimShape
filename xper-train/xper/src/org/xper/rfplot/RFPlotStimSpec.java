package org.xper.rfplot;

import com.thoughtworks.xstream.XStream;
import org.xper.rfplot.drawing.RFPlotDrawable;

public class RFPlotStimSpec {
	/**
	 * Class name of the RFPlotObject
	 */
	String stimClass;
	/**
	 * Spec for the RFPlotObject
	 */
	String stimSpec;

	public RFPlotStimSpec() {
	}

	public RFPlotStimSpec(String stimClass, String stimSpec) {
		this.stimClass = stimClass;
		this.stimSpec = stimSpec;
	}

	boolean animation = true;
	transient static XStream s;

	static {
		s = new XStream();
		s.alias("StimSpec", RFPlotStimSpec.class);
		s.useAttributeFor("animation", boolean.class);
	}

	public String toXml () {
		return RFPlotStimSpec.toXml(this);
	}

	public static String toXml (RFPlotStimSpec spec) {
		return s.toXML(spec);
	}

	public static RFPlotStimSpec fromXml (String xml) {
		if (xml == null) return null;
		RFPlotStimSpec spec = (RFPlotStimSpec)s.fromXML(xml);
		return spec;
	}

	public static RFPlotStimSpec fromRFPlotDrawable(RFPlotDrawable drawable){
		String stimSpec = drawable.getSpec();
		String stimClass = drawable.getClass().getName();

		return new RFPlotStimSpec(stimClass, stimSpec);
	}

	public static String getStimSpecFromRFPlotDrawable(RFPlotDrawable drawable){

		RFPlotStimSpec rfPlotStimSpec = RFPlotStimSpec.fromRFPlotDrawable(drawable);
		return rfPlotStimSpec.toXml();
	}

	public String getStimClass() {
		return stimClass;
	}
	public void setStimClass(String stimClass) {
		this.stimClass = stimClass;
	}
	public String getStimSpec() {
		return stimSpec;
	}
	public void setStimSpec(String stimSpec) {
		this.stimSpec = stimSpec;
	}

	public static class XmlCharacterReplacer {

		/**
		 * We don't need to do this... It works fine with the unescaped characters in the xml string.
		 *
		 * Replaces escaped XML characters in the input string with their corresponding special characters.
		 * It's crucial to replace "&amp;" last to avoid incorrect conversion of already replaced entities.
		 *
		 * @param input The input string containing escaped XML characters.
		 * @return A new string with escaped characters replaced by XML special characters.
		 */
		public static String replaceEscapedCharacters(String input) {
			if (input == null) {
				return null;
			}
			// First replace all specific entities except &amp;
			String temp = input
					.replace("&lt;", "<")
					.replace("&gt;", ">")
					.replace("&quot;", "\"")
					.replace("&apos;", "'");

			// Replace &amp; last to ensure correct decoding
			return temp.replace("&amp;", "&");
		}
	}
}