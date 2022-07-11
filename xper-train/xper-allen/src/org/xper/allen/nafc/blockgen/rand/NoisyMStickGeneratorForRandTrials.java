package org.xper.allen.nafc.blockgen.rand;

import java.util.LinkedList;
import java.util.List;

import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.FromRandLeafMStickGenerator;
import org.xper.allen.drawing.composition.MStickGenerationException;
import org.xper.allen.drawing.composition.MStickGenerator;
import org.xper.allen.drawing.composition.metricmorphs.MetricMorphMStickGenerator;
import org.xper.allen.drawing.composition.metricmorphs.MetricMorphParameterGenerator;
import org.xper.allen.drawing.composition.metricmorphs.MetricMorphParams;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphMStickGenerator;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphParameterGenerator;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphParams;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;

public class NoisyMStickGeneratorForRandTrials {
	private AbstractMStickPngTrialGenerator generator;
	private RandNoisyTrialParameters trialParameters;


	public NoisyMStickGeneratorForRandTrials(AbstractMStickPngTrialGenerator generator,
			RandNoisyTrialParameters trialParameters) {
		super();
		this.generator = generator;
		this.trialParameters = trialParameters;

		generate();
	}

	private boolean tryagain = true;
	private AllenMatchStick sample;
	private AllenMatchStick match;
	private List<AllenMatchStick> qualitativeMorphDistractors = new LinkedList<AllenMatchStick>();


	private void generate() {
		assignMetricMorphParameters();
		assignQualitativeMorphParameters();
		while (tryagain) {
			try {
				tryGenerateSample();
			} catch (Exception e) {
//				e.printStackTrace();
				continue;
			}

			try {
				tryGenerateMatch();
			} catch (Exception e) {
				continue;
			}

			try {
				tryGenerateQualitativeMorphDistractors();
			} catch (Exception e) {
//				e.printStackTrace();
				continue;
			}

			tryagain = false;
		}
	}

	private void reset() {
		sample = new AllenMatchStick();
		match = new AllenMatchStick();
		qualitativeMorphDistractors = new LinkedList<AllenMatchStick>();
	}

	private void tryGenerateSample() {
		FromRandLeafMStickGenerator sampleGenerator = new FromRandLeafMStickGenerator(generator);
		sample = sampleGenerator.tryGenerate();
	}

	private void tryGenerateMatch() {
		MetricMorphMStickGenerator matchGenerator = new MetricMorphMStickGenerator(generator, sample, mmp);
		match = matchGenerator.tryGenerate();
	}

	private void tryGenerateQualitativeMorphDistractors() {
		for (QualitativeMorphParams qmp:qmps) {
			QualitativeMorphMStickGenerator qmGenerator = new QualitativeMorphMStickGenerator(generator, sample, qmp);
			qualitativeMorphDistractors.add(qmGenerator.tryGenerate());
		}
	}

	MetricMorphParams mmp;
	private void assignMetricMorphParameters() {
		MetricMorphParameterGenerator mmpGenerator = generator.getMmpGenerator();
		mmp = new MetricMorphParams();
		mmp = mmpGenerator.getMMP(trialParameters.getSize(), trialParameters.numMorphCategories.getNumMMCategories());
	}

	List<QualitativeMorphParams> qmps;
	private void assignQualitativeMorphParameters() {
		QualitativeMorphParameterGenerator qmpGenerator = generator.getQmpGenerator();
		qmps = new LinkedList<QualitativeMorphParams>();
		for(int qmIndx = 0; qmIndx<trialParameters.numDistractors.getNumQMDistractors(); qmIndx++) {
			qmps.add(qmpGenerator.getQMP(trialParameters.numMorphCategories.getNumQMCategories()));
		}
	}

	public AllenMatchStick getSample() {
		return sample;
	}

	public AllenMatchStick getMatch() {
		return match;
	}

	public List<AllenMatchStick> getQualitativeMorphDistractors() {
		return qualitativeMorphDistractors;
	}




}
