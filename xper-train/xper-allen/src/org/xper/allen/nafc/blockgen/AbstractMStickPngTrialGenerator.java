package org.xper.allen.nafc.blockgen;

import java.util.LinkedList;
import java.util.List;

import org.xper.Dependency;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.metricmorphs.MetricMorphParameterGenerator;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphParameterGenerator;
import org.xper.allen.util.AllenDbUtil;
import org.xper.time.TimeUtil;

public abstract class AbstractMStickPngTrialGenerator extends AbstractTrialGenerator {

	@Dependency
	protected AllenDbUtil dbUtil;
	@Dependency
	protected TimeUtil globalTimeUtil;
	@Dependency
	protected String generatorPngPath;
	@Dependency
	protected String experimentPngPath;
	@Dependency
	protected String generatorSpecPath;
	@Dependency
	protected AllenPNGMaker pngMaker;
	@Dependency
	private double maxImageDimensionDegrees;

	public AbstractMStickPngTrialGenerator() {
		super();
	}

	public List<String> convertPathsToExperiment(List<String> generatorPaths) {
		LinkedList<String> expPaths = new LinkedList<String>();
		for(int s=0; s<generatorPaths.size(); s++) {
			String newPath = generatorPaths.get(s).replace(getGeneratorPngPath(), getExperimentPngPath());
			expPaths.add(s, newPath);
		}
		return expPaths;
	}

	public String convertPathToExperiment(String generatorPath) {
	
		String newPath = generatorPath.replace(getGeneratorPngPath(), getExperimentPngPath());
	
		return newPath;
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

	public String getGeneratorSpecPath() {
		return generatorSpecPath;
	}

	public void setGeneratorSpecPath(String generatorSpecPath) {
		this.generatorSpecPath = generatorSpecPath;
	}

	public AllenPNGMaker getPngMaker() {
		return pngMaker;
	}

	public void setPngMaker(AllenPNGMaker pngMaker) {
		this.pngMaker = pngMaker;
	}

	public double getMaxImageDimensionDegrees() {
		return maxImageDimensionDegrees;
	}

	public void setMaxImageDimensionDegrees(double maxImageDimensionDegrees) {
		this.maxImageDimensionDegrees = maxImageDimensionDegrees;
	}

}