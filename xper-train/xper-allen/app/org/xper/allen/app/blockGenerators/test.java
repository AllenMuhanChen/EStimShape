package org.xper.allen.app.blockGenerators;

import java.util.ArrayList;

import org.xper.allen.specs.GaussSpec;
import org.xper.allen.util.AllenXMLUtil;;
public class test {

	public static void main(String[] args) {
		AllenXMLUtil xmlUtil = new AllenXMLUtil();
		ArrayList<GaussSpec> gaussSpecs = (ArrayList<GaussSpec>) xmlUtil.parseFile("/Users/allenchen/Documents/GitHub/V1Microstim/xper-train/xper-allen/doc/Test.xml");
		System.out.println(gaussSpecs.get(0).getBrightness());
	}

}
