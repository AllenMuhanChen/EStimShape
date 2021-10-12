package org.xper.generate;

import java.util.ArrayList;
import java.util.List;

import org.xper.drawing.drawables.PNGmaker;
import org.xper.drawing.stick.MStickSpec;
import org.xper.drawing.stick.MatchStick;
import org.xper.utils.RGBColor;

public class generateStimuli {
	public static void main(String[] args) {
		// args 0 - path
		// args 1 - start id
		// args 2 - nStim
		// args 3 - texture
		// args 4 - scale
		// args 5 - saveSpec
		// args 6 - saveVertSpec
		
		// args 7 - contrast
		// args 8-10 - foreground color
		// args 11-13 - background color
		
		// args 14-15 - width, height
		String folderPath = args[0];
		List<Long> ids = new ArrayList<Long>();
		List<MatchStick> objs = new ArrayList<MatchStick>();
		
		double contrast = Double.parseDouble(args[7]);
		RGBColor foreColor = new RGBColor(Float.parseFloat(args[ 8]),Float.parseFloat(args[ 9]),Float.parseFloat(args[10]));
		RGBColor backColor = new RGBColor(Float.parseFloat(args[11]),Float.parseFloat(args[12]),Float.parseFloat(args[13]));

		for (int i=0; i<Integer.parseInt(args[2]); i++) {		
			ids.add((long)(Integer.parseInt(args[1])+i));
			objs.add(new MatchStick());
			
			// set object properties
			objs.get(i).setScale(Double.parseDouble(args[4]));
			// objs.get(i).setDoCenterObject(true);
			objs.get(i).setStimColor(foreColor);
			objs.get(i).setContrast(contrast);
			if (args[3].equals("RAND"))
				if (Math.random() > 0.5)
					objs.get(i).setTextureType("SHADE");
				else
					objs.get(i).setTextureType("SPECULAR");
			else
				objs.get(i).setTextureType(args[3]);
			
			// generate object
			objs.get(i).genMatchStickRand();
			
			// save spec, if necessary
			if (Boolean.parseBoolean(args[5])) {
				MStickSpec spec = new MStickSpec();
				spec.setMStickInfo(objs.get(i));
				spec.writeInfo2File(folderPath + "/" + ids.get(i), Boolean.parseBoolean(args[6]));
			}
		}
		// make all the images
		PNGmaker pngMaker = new PNGmaker(Integer.parseInt(args[14]), Integer.parseInt(args[15]));
		pngMaker.setBackColor(backColor);
		pngMaker.createAndSavePNGsfromObjs(objs, ids, folderPath);
	}
}