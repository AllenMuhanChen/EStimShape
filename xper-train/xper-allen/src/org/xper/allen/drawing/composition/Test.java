package org.xper.allen.drawing.composition;

import java.util.ArrayList;
import java.util.List;

import org.xper.alden.drawing.drawables.PNGmaker;
import org.xper.drawing.stick.MStickSpec;
import org.xper.drawing.stick.MatchStick;
import org.xper.utils.RGBColor;

import com.thoughtworks.xstream.XStream;

public class Test {


	public static void main(String[] args) throws Exception {
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
		List<Long> ids2 = new ArrayList<Long>();

		List<AllenMatchStick> objs = new ArrayList<AllenMatchStick>();
		List<AllenMatchStick> objs2 = new ArrayList<AllenMatchStick>();
		List<AllenMatchStick> objs3 = new ArrayList<AllenMatchStick>();
		List<ArrayList<AllenMatchStick>> variations = new ArrayList<ArrayList<AllenMatchStick>>();
		variations.add((ArrayList<AllenMatchStick>) objs);
		variations.add((ArrayList<AllenMatchStick>) objs2);
		variations.add((ArrayList<AllenMatchStick>) objs3);
		
		double contrast = Double.parseDouble(args[7]);
		RGBColor foreColor = new RGBColor(Float.parseFloat(args[ 8]),Float.parseFloat(args[ 9]),Float.parseFloat(args[10]));
		RGBColor backColor = new RGBColor(Float.parseFloat(args[11]),Float.parseFloat(args[12]),Float.parseFloat(args[13]));

		//FOR ALL OF OUR VARIATIONS, APPLY SAME BASE PARAMETERS
		for (int h=0; h<2; h++){	

			for (int i=0; i<Integer.parseInt(args[2]); i++) {	
				//TODO: make list of ids to scale this up with new scaled objs list list.
				ids.add((long)(Integer.parseInt(args[1])+i));
				variations.get(h).add(new AllenMatchStick());
				// set object properties
				variations.get(h).get(i).setScale(Double.parseDouble(args[4]));
				// objs.get(i).setDoCenterObject(true);
				variations.get(h).get(i).setStimColor(foreColor);
				variations.get(h).get(i).setContrast(contrast);
				if (args[3].equals("RAND"))
					if (Math.random() > 0.5) {
						variations.get(h).get(i).setTextureType("SHADE");}
					else {
						variations.get(h).get(i).setTextureType("SPECULAR");}
				else {
					variations.get(h).get(i).setTextureType(args[3]);}
				//DIVERGE INTO DIFFERENT VARIATIONS
				ids2.add((long)(Integer.parseInt(args[1])+i+100));
			}
		}
		
		//GENERATE BASE MATCHSTICK - only for training, for real experiment should choose limb from GA. 
		//SPECIFY A LIMB
		//GENERATE NEW STRUCTURE FROM LIMB
		//COPY NEW STRUCTURE INTO NEW VARIATIONS
		//MODIFY EACH NEW VARIATION
		for (int i=0; i<Integer.parseInt(args[2]); i++) {
			// GENERATE OBJECT
			objs.get(i).genMatchStickRand();
			
			//GENERATE FROM RANDOM LEAF 
			int randomLeaf = objs.get(i).chooseRandLeaf();
			//objs2.get(i).copyFrom(objs.get(i));
			objs2.get(i).genMatchStickFromLeaf(objs.get(i).getTubeComp(randomLeaf));
			
			//REMOVE A RANDOM LEAF
			/*
			objs3.get(i).copyFrom(objs2.get(i));;
			objs3.get(i).genRemovedLeafMatchStick();
			*/
			// save spec, if necessary
			if (Boolean.parseBoolean(args[5])) {
				MStickSpec spec = new MStickSpec();
				spec.setMStickInfo(objs.get(i));
				spec.writeInfo2File(folderPath + "/" + ids.get(i), Boolean.parseBoolean(args[6]));
			}
		}


		// make all the images
		AllenPNGMaker pngMaker = new AllenPNGMaker(Integer.parseInt(args[14]), Integer.parseInt(args[15]));
		pngMaker.setBackColor(backColor);
		pngMaker.createAndSavePNGsfromObjs(objs, ids, folderPath);
		pngMaker.createAndSavePNGsfromObjs(objs2, ids2, folderPath);

	}
}
