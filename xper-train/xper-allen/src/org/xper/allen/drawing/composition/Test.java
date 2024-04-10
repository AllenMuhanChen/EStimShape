package org.xper.allen.drawing.composition;

import java.util.ArrayList;
import java.util.List;

import org.xper.alden.drawing.drawables.PNGmaker;
import org.xper.drawing.stick.MStickSpec;
import org.xper.drawing.stick.MatchStick;
import org.xper.drawing.stick.TubeComp;
import org.xper.drawing.RGBColor;

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

		int numVariations = 5;

		List<ArrayList<Long>> variationIds = new ArrayList<ArrayList<Long>>();


		List<AllenMatchStick> obj_orig = new ArrayList<AllenMatchStick>();
		List<AllenMatchStick> objs_match = new ArrayList<AllenMatchStick>();
		List<AllenMatchStick> objs_leafMorph1 = new ArrayList<AllenMatchStick>();
		List<AllenMatchStick> objs_leafMorph2 = new ArrayList<AllenMatchStick>();
		List<AllenMatchStick> objs_leafMorph3 = new ArrayList<AllenMatchStick>();
		List<ArrayList<AllenMatchStick>> variations = new ArrayList<ArrayList<AllenMatchStick>>();
		variations.add((ArrayList<AllenMatchStick>) obj_orig);
		variations.add((ArrayList<AllenMatchStick>) objs_match);
		variations.add((ArrayList<AllenMatchStick>) objs_leafMorph1);
		variations.add((ArrayList<AllenMatchStick>) objs_leafMorph2);
		variations.add((ArrayList<AllenMatchStick>) objs_leafMorph3);

		double contrast = Double.parseDouble(args[7]);
		RGBColor foreColor = new RGBColor(Float.parseFloat(args[ 8]),Float.parseFloat(args[ 9]),Float.parseFloat(args[10]));
		RGBColor backColor = new RGBColor(Float.parseFloat(args[11]),Float.parseFloat(args[12]),Float.parseFloat(args[13]));

		//FOR ALL OF OUR VARIATIONS, APPLY SAME BASE PARAMETERS
		for (int h=0; h<numVariations; h++){
			variationIds.add(new ArrayList<Long>());
			for (int i=0; i<Integer.parseInt(args[2]); i++) {
				variationIds.get(h).add((long)(Integer.parseInt(args[1])+i+h*1000));
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
				}
			}
		}
		//GENERATE BASE MATCHSTICK - only for training, for real experiment should choose limb from GA.
		//SPECIFY A LIMB
		//GENERATE NEW STRUCTURE FROM LIMB
		//MATCH & SAMPLE
		//COPY NEW STRUCTURE INTO NEW VARIATIONS
		//DISTRACTORS
		//MORPH SELECTED LIMB
		// ...
		//MODIFY EACH NEW VARIATION
		for (int i=0; i<Integer.parseInt(args[2]); i++) {
			// GENERATE OBJECT
			obj_orig.get(i).genMatchStickRand();

			//GENERATE FROM RANDOM LEAF
			int randomLeaf = obj_orig.get(i).chooseRandLeaf();
			objs_match.get(i).genMatchStickFromLeaf(randomLeaf, obj_orig.get(i));

			//MORPH JUST THE LEAF
			int leafToMorphIndx = 1; //The randomly chosen leaf before should be the first component
			boolean maintainTangent = true;
			objs_leafMorph1.get(i).genReplacedLeafMatchStick(leafToMorphIndx, objs_match.get(i), maintainTangent);
			objs_leafMorph2.get(i).genReplacedLeafMatchStick(leafToMorphIndx, objs_match.get(i), maintainTangent);
			objs_leafMorph3.get(i).genReplacedLeafMatchStick(leafToMorphIndx, objs_match.get(i), maintainTangent);

			//REMOVE A RANDOM LEAF
			/*
			objs3.get(i).copyFrom(objs2.get(i));;
			objs3.get(i).genRemovedLeafMatchStick();
			 */
			// save spec, if necessary

		}

//		for (int h=0; h<numVariations; h++){
//			for (int i=0; i<Integer.parseInt(args[2]); i++){
//				if (Boolean.parseBoolean(args[5])) {
//					MStickSpec spec = new MStickSpec();
//					spec.setMStickInfo(variations.get(h).get(i));
//					spec.writeInfo2File(folderPath + "/" + variationIds.get(h).get(i), Boolean.parseBoolean(args[6]));
//				}
//			}
//			// make all the images
//			AllenPNGMaker pngMaker = new AllenPNGMaker(Integer.parseInt(args[14]), Integer.parseInt(args[15]));
//			//pngMaker.setBackColor(backColor);
//			//pngMaker.createAndSavePNGsfromObjs(variations.get(h), variationIds.get(h), folderPath);
//
//
//
//		}

	}
}