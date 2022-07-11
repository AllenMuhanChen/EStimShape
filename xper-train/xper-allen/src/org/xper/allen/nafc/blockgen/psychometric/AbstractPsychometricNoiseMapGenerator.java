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
public class AbstractPsychometricNoiseMapGenerator extends AbstractMStickPngTrialGenerator {

	@Dependency
	String generatorPsychometricNoiseMapPath;
	@Dependency
	String experimentPsychometricNoiseMapPath;

	public AbstractPsychometricNoiseMapGenerator() {
		super();
	}

	public List<String> convertNoiseMapPathsToExperiment(List<String> generatorPaths) {
		LinkedList<String> expPaths = new LinkedList<String>();
		for(int s=0; s<generatorPaths.size(); s++) {
			String newPath = convertNoiseMapPathToExperiment(generatorPaths.get(s));
			expPaths.add(s, newPath);
		}
		return expPaths;
	}

	public String convertNoiseMapPathToExperiment(String generatorPath) {
		return generatorPath.replace(getGeneratorPsychometricNoiseMapPath(), getExperimentPsychometricNoiseMapPath());
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

}