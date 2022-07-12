package org.xper.allen.nafc.blockgen.rand;

import java.util.LinkedList;
import java.util.List;

import org.xper.allen.drawing.composition.AbstractMStickGenerator;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.FromRandLeafMStickGenerator;
import org.xper.allen.drawing.composition.MStickGenerationException;
import org.xper.allen.drawing.composition.MStickGenerator;
import org.xper.allen.drawing.composition.RandMStickGenerator;
import org.xper.allen.drawing.composition.metricmorphs.MetricMorphMStickGenerator;
import org.xper.allen.drawing.composition.metricmorphs.MetricMorphParameterGenerator;
import org.xper.allen.drawing.composition.metricmorphs.MetricMorphParams;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphMStickGenerator;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphParameterGenerator;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphParams;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.nafc.blockgen.NAFCMatchSticks;

public class MStickGeneratorForRandTrials {
	private AbstractMStickPngTrialGenerator generator;
	private RandNoisyTrialParameters trialParameters;


	public MStickGeneratorForRandTrials(AbstractMStickPngTrialGenerator generator,
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
	private List<AllenMatchStick> randDistractors = new LinkedList<AllenMatchStick>();

	private void generate() {
		assignMetricMorphParameters();
		assignQualitativeMorphParameters();
		while (tryagain) {
			try {
				tryGenerateSample();
			} catch (Exception e) {
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
				continue;
			}

			try {
				tryGenerateRandomDistractors();
			} catch (Exception e) {
				continue;
			}
			tryagain = false;
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

	private void tryGenerateSample() {
		AbstractMStickGenerator sampleGenerator = new FromRandLeafMStickGenerator(generator);
		sample = sampleGenerator.getMStick();
	}

	private void tryGenerateMatch() {
		AbstractMStickGenerator matchGenerator = new MetricMorphMStickGenerator(generator, sample, mmp);
		match = matchGenerator.getMStick();
	}

	private void tryGenerateQualitativeMorphDistractors() {
		for (QualitativeMorphParams qmp:qmps) {
			AbstractMStickGenerator qmGenerator = new QualitativeMorphMStickGenerator(generator, sample, qmp);
			qualitativeMorphDistractors.add(qmGenerator.getMStick());
		}
	}

	private void tryGenerateRandomDistractors() {
		for(int i=0; i<trialParameters.getNumDistractors().getNumRandDistractors(); i++) {
			AbstractMStickGenerator randGenerator = new RandMStickGenerator(generator);
			randDistractors.add(randGenerator.getMStick());
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

	public List<AllenMatchStick> getRandDistractors() {
		return randDistractors;
	}

	
	public NAFCMatchSticks getNAFCMatchSticks() {
		NAFCMatchSticks matchSticks = new NAFCMatchSticks();
		matchSticks.setSampleMStick(sample);
		matchSticks.setMatchMStick(match);
		List<AllenMatchStick> distractors = new LinkedList<AllenMatchStick>();
		distractors.addAll(qualitativeMorphDistractors);
		distractors.addAll(randDistractors);
		return matchSticks;
		
	}



}
