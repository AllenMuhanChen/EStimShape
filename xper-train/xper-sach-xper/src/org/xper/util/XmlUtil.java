package org.xper.util;

import org.dom4j.Document;
import org.dom4j.DocumentException;
import org.dom4j.DocumentHelper;
import org.dom4j.Node;
import org.xper.exception.XmlDocInvalidFormatException;
import org.xper.experiment.ExperimentTask;

public class XmlUtil {
	public static Document parseSpec(String xml) {
		try {
			Document doc = DocumentHelper.parseText(xml);
			return doc;
		} catch (DocumentException e) {
			throw new XmlDocInvalidFormatException("Invalid spec: " + xml);
		}
	}
	
	public static boolean isAnimation(Document doc, String xpath) {
		try {
			Node animation = doc.selectSingleNode(xpath);
			return isAnimation(animation);
		} catch (NullPointerException e) {
			throw new XmlDocInvalidFormatException("No " + xpath + " node.");
		}
	}
	
	public static boolean isAnimation(Node node) {
		String animation = node.valueOf("@animation");
		if (animation == null) {
			return false;
		}
		return animation.equalsIgnoreCase("true");
	}
	
	public static boolean slideIsAnimation(ExperimentTask task) {
		if (task == null) {
			return false;
		}
		String xml = task.getStimSpec();
		Document doc = XmlUtil.parseSpec(xml);
		return XmlUtil.isAnimation(doc, "/StimSpec");
	}
	
	public static boolean isStereo(Node node) {
		String animation = node.valueOf("@stereo");
		if (animation == null) {
			return false;
		}
		return animation.equalsIgnoreCase("true");
	}
	
	public static boolean isStereo(Document doc, String xpath) {
		try {
			Node s = doc.selectSingleNode(xpath);
			return isStereo(s);
		} catch (NullPointerException e) {
			throw new XmlDocInvalidFormatException("No " + xpath + " node.");
		}
	}
	
	public static boolean slideIsStereo(ExperimentTask task) {
		if (task == null) {
			return false;
		}
		String xml = task.getStimSpec();
		Document doc = XmlUtil.parseSpec(xml);
		return XmlUtil.isStereo(doc, "/StimSpec");
	}
}
