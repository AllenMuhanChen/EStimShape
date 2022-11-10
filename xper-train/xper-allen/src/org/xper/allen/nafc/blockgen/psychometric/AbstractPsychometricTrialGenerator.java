package org.xper.allen.nafc.blockgen.psychometric;

import java.util.LinkedList;
import java.util.List;

import org.xper.Dependency;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;

/**
 * AbstractNoiseMapTrialGenerator IS a MStickPngTrialGenerator as well. 
 * @author r2_allen
 *
 */
public abstract class AbstractPsychometricTrialGenerator extends AbstractMStickPngTrialGenerator {
	@Dependency
	String generatorPsychometricPngPath;
	@Dependency
	String experimentPsychometricPngPath;
	@Dependency
	String generatorPsychometricNoiseMapPath;
	@Dependency
	String experimentPsychometricNoiseMapPath;
	@Dependency
	String generatorPsychometricSpecPath;
	
	public AbstractPsychometricTrialGenerator() {
		super();
	}

	public List<String> convertPsychometricPathsToExperiment(List<String> generatorPaths) {
		LinkedList<String> expPaths = new LinkedList<String>();
		for(int s=0; s<generatorPaths.size(); s++) {
			String newPath = convertPsychometricToExperiment(generatorPaths.get(s));
			expPaths.add(s, newPath);
		}
		return expPaths;
	}


	public String convertPsychometricToExperiment(String generatorPath) {
		if(generatorPath.contains(generatorPsychometricNoiseMapPath))
			return generatorPath.replace(generatorPsychometricNoiseMapPath, experimentPsychometricNoiseMapPath);
		else if (generatorPath.contains(generatorPsychometricPngPath)) {
			return generatorPath.replace(generatorPsychometricPngPath, experimentPsychometricPngPath);
			}
		else {
			throw new RuntimeException("Given generatorPath does not contain base path for"
					+ "psychometric noisemap paths or png paths");
		}
	}

	public String getGeneratorPsychometricNoiseMapPath() {
		return generatorPsychometricNoiseMapPath;
	}

	public void setGeneratorPsychometricNoiseMapPath(String generatorPsychometricNoiseMapPath) {
		this.generatorPsychometricNoiseMapPath = generatorPsychometricNoiseMapPath;
	}

	public String getExperimentPsychometricNoiseMapPath() {
		return experimentPsychometricNoiseMapPath;
	}

	public void setExperimentPsychometricNoiseMapPath(String experimentPsychometricNoiseMapPath) {
		this.experimentPsychometricNoiseMapPath = experimentPsychometricNoiseMapPath;
	}

	public String getGeneratorPsychometricPngPath() {
		return generatorPsychometricPngPath;
	}

	public void setGeneratorPsychometricPngPath(String generatorPsychometricPngPath) {
		this.generatorPsychometricPngPath = generatorPsychometricPngPath;
	}

	public String getExperimentPsychometricPngPath() {
		return experimentPsychometricPngPath;
	}

	public void setExperimentPsychometricPngPath(String experimentPsychometricPngPath) {
		this.experimentPsychometricPngPath = experimentPsychometricPngPath;
	}

	public String getGeneratorPsychometricSpecPath() {
		return generatorPsychometricSpecPath;
	}

	public void setGeneratorPsychometricSpecPath(String generatorPsychometricSpecPath) {
		this.generatorPsychometricSpecPath = generatorPsychometricSpecPath;
	}



}