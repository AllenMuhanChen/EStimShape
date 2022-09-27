package org.xper.allen.app.fixation;

import java.io.File;
import java.util.Random;

import org.xper.Dependency;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.rfplot.drawing.png.PngSpec;
import org.xper.allen.util.AllenDbUtil;
import org.xper.drawing.Coordinates2D;
import org.xper.exception.VariableNotFoundException;
import org.xper.time.TimeUtil;

import static org.xper.allen.nafc.blockgen.NAFCCoordinateAssigner.randomCoordsWithinRadii;

public class FixationPngBlockGen extends AbstractMStickPngTrialGenerator {
	@Dependency
	AllenDbUtil dbUtil;
	@Dependency
	TimeUtil globalTimeUtil;
	@Dependency
	String generatorPngPath;
	@Dependency
	String experimentPngPath;

	/**
	 * Selects visual stimuli randomly from stimTypes
	 */
	Random r = new Random();
	long genId = 1;
	public void generate(int numTrials, double scale,
			double radiusLowerLim, double radiusUpperLim) {
		experimentPngPath = experimentPngPath+"/";
		//FILEPATH
		File folder = new File(generatorPngPath);
		File[] fileArray = folder.listFiles();

		ImageDimensions pngDimensions = new ImageDimensions(scale, scale);

		try {
			genId = dbUtil.readReadyGenerationInfo().getGenId() + 1;
		} catch(VariableNotFoundException e) {
			dbUtil.writeReadyGenerationInfo(genId, 0);
		}
		for (int i=0; i<numTrials; i++) {
			long taskId = globalTimeUtil.currentTimeMicros();
			int randomPngIndex = r.nextInt(fileArray.length);
			Coordinates2D pngLocation = randomCoordsWithinRadii(radiusLowerLim, radiusUpperLim);
			String experimentPath = experimentPngPath+fileArray[randomPngIndex].getName();
			PngSpec pngSpec = new PngSpec(pngLocation.getX(), pngLocation.getY(), pngDimensions, experimentPath);
			dbUtil.writeStimObjData(taskId, pngSpec.toXml(), "");

			dbUtil.writeStimSpec(taskId, pngSpec.toXml());
			dbUtil.writeTaskToDo(taskId,taskId, -1, genId);
		}
		dbUtil.updateReadyGenerationInfo(genId, numTrials);
		System.out.println("Done Generating...");
		return;
	}
	public AllenDbUtil getDbUtil() {
		return dbUtil;
	}
	public void setDbUtil(AllenDbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}
	public TimeUtil getGlobalTimeUtil() {
		return globalTimeUtil;
	}
	public void setGlobalTimeUtil(TimeUtil globalTimeUtil) {
		this.globalTimeUtil = globalTimeUtil;
	}
	public String getGeneratorPngPath() {
		return generatorPngPath;
	}
	public void setGeneratorPngPath(String generatorPngPath) {
		this.generatorPngPath = generatorPngPath;
	}
	public String getExperimentPngPath() {
		return experimentPngPath;
	}
	public void setExperimentPngPath(String experimentPngPath) {
		this.experimentPngPath = experimentPngPath;
	}
}
