package org.xper.sach.util;

import org.dom4j.Document;
import org.dom4j.Node;
import org.xper.drawing.Coordinates2D;

public class SachXmlUtil {
	
	static Coordinates2D getCooridates2D(Node n) {
		String x = n.selectSingleNode("x").getText();
		String y = n.selectSingleNode("y").getText();
		return new Coordinates2D(Double.parseDouble(x), Double.parseDouble(y));
	}
	
	
	public static long getReward(Document doc) {
		Node n = doc.selectSingleNode("/StimSpec/reward");
		String s = n.getText();
		return Long.parseLong(s);
	}
}
