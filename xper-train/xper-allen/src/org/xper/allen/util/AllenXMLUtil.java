package org.xper.allen.util;

import java.io.File;
import java.io.FileInputStream;
import java.util.ArrayList;

import org.xper.allen.saccade.blockgen.TrainingTrial;
import org.xper.allen.specs.GaussSpec;

import com.thoughtworks.xstream.XStream;
public class AllenXMLUtil {
	XStream s = new XStream();
	
	public AllenXMLUtil() {
		s.alias("list", ArrayList.class);
		s.alias("VisualTrial", TrainingTrial.class);

	}
	
	public Object parseFile(String filepath) {
		try {
			File xmlFile = new File(filepath);
			System.out.println(s.toString());
			Object ret = s.fromXML(new FileInputStream(xmlFile));
			return ret;
		}catch(Exception e){
			e.printStackTrace();
		}
		return null;
	}
	
	
	/*
	public static Document parseFile(String filepath) {
		try {
			File file = new File(filepath);
			DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
			DocumentBuilder db = dbf.newDocumentBuilder();
			Document doc = db.translate(file);
			doc.getDocumentElement().normalize();
			System.out.println(doc.toString());
			return doc;
		}catch(Exception e) {
			e.printStackTrace();
		}
		return null;
	}
	*/
	/*
	public static getXCenter(Document doc) {
		NodeList nodeList = doc.getElementsByTagName("StimSpec");
		
	}
	*/
}
