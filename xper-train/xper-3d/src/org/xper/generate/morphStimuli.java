package org.xper.generate;

import java.io.BufferedReader;
import java.io.FileReader;
import java.util.ArrayList;
import java.util.List;

import org.xper.alden.drawing.drawables.PNGmaker;
import org.xper.drawing.stick.MStickSpec;
import org.xper.drawing.stick.MatchStick;
import org.xper.drawing.RGBColor;

public class morphStimuli {
	public static void main(String[] argsFile) {
		String textPath = argsFile[0];
		try {
			FileReader fr = new FileReader(textPath);
	        BufferedReader br = new BufferedReader(fr);

			List<Long> ids = new ArrayList<Long>();
			List<MatchStick> objs = new ArrayList<MatchStick>();
			String folderPath = "";
			RGBColor backColor = new RGBColor(0.3,0.3,0.3);

			int obj_counter=0;
	        for (String line = br.readLine(); line != null; line = br.readLine()) {
	            String[] args = line.split(";");
				// args 0 - path
				// args 1 - parent id
				// args 2 - child id
				// args 3 - nMorph
				// args 4 - texture
				// args 5 - contrast
				// args 6 - scale
				// args 7 - saveSpec
				// args 8 - saveVertSpec

		    		// args 9-11 - foreground color
		    		// args 12-14 - background color

				folderPath = args[0].trim();
	            long parentId = Long.parseLong(args[1].trim());
				long childId = Long.parseLong(args[2].trim());
				int nMorphs = Integer.parseInt(args[3].trim());
				double contrast = Double.parseDouble(args[5].trim());
				double scale = Double.parseDouble(args[6].trim());
				RGBColor foreColor = new RGBColor(Float.parseFloat(args[ 9].trim()),Float.parseFloat(args[10].trim()),Float.parseFloat(args[11].trim()));
				backColor = new RGBColor(Float.parseFloat(args[12].trim()),Float.parseFloat(args[13].trim()),Float.parseFloat(args[14].trim()));

				ids.add(childId);

				objs.add(new MatchStick());
				objs.get(obj_counter).setScale(scale);
				objs.get(obj_counter).setContrast(contrast);
				objs.get(obj_counter).setStimColor(foreColor);
				objs.get(obj_counter).genMatchStickFromFile(folderPath + "/" + parentId + "_spec.xml",new double[]{0,0,0});

				if (nMorphs > 0)
					objs.get(obj_counter).mutateNtimes(-1, nMorphs);

				objs.get(obj_counter).setTextureType(args[4].trim());

				if (Boolean.parseBoolean(args[7].trim())) {
					MStickSpec spec = new MStickSpec();
					spec.setMStickInfo(objs.get(obj_counter));
					spec.writeInfo2File(folderPath + "/" + ids.get(obj_counter), Boolean.parseBoolean(args[8].trim()));
				}

				obj_counter++;
	        }
			fr.close();
			br.close();

			PNGmaker pngMaker = new PNGmaker();
			pngMaker.setBackColor(backColor);
			pngMaker.createAndSavePNGsfromObjs(objs, ids, folderPath);
		}
		catch(Exception e) {
			System.err.println("Error: during batch generation");
		}
	}
}