package org.xper.allen.nafc.blockgen.rand;

import java.util.LinkedList;
import java.util.List;

import org.xper.allen.drawing.composition.AbstractMStickGenerator;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.FromRandLeafMStickGenerator;
import org.xper.allen.drawing.composition.RandMStickGenerator;
import org.xper.allen.drawing.composition.metricmorphs.MetricMorphMStickGenerator;
import org.xper.allen.drawing.composition.metricmorphs.MetricMorphParameterGenerator;
import org.xper.allen.drawing.composition.metricmorphs.MetricMorphParams;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphMStickGenerator;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphParameterGenerator;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphParams;

public class MStickGeneratorForRandTrials {
	private final double maxImageDimensionDegrees;
	private RandNoisyTrialParameters trialParameters;

	public MStickGeneratorForRandTrials(double maxImageDimensionDegrees, RandNoisyTrialParameters trialParameters) {
		this.maxImageDimensionDegrees = maxImageDimensionDegrees;
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
		
		//a qualitative Morph distractor or metric morph match can fail
		//due to poor sample generation, so if we fail downstream, let's
		//restart at the beginning. 
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

			tryagain = false;
		}
		
		//We shouldn't restart from the beginning if random distractors fail because
		//it doesn't rely on previous generation at all. 
		tryagain = true;
		while(tryagain) {

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
		MetricMorphParameterGenerator mmpGenerator = new MetricMorphParameterGenerator();
		mmp = new MetricMorphParams();
		mmp = mmpGenerator.getMMP(trialParameters.getSize(), trialParameters.numMorphCategories.getNumMMCategories());
	}

	List<QualitativeMorphParams> qmps;
	private void assignQualitativeMorphParameters() {
		QualitativeMorphParameterGenerator qmpGenerator = new QualitativeMorphParameterGenerator(maxImageDimensionDegrees);
		qmps = new LinkedList<QualitativeMorphParams>();
		for(int qmIndx = 0; qmIndx<trialParameters.numDistractors.getNumQMDistractors(); qmIndx++) {
			qmps.add(qmpGenerator.getQMP(trialParameters.numMorphCategories.getNumQMCategories()));
		}
	}

	private void tryGenerateSample() {
		AbstractMStickGenerator sampleGenerator = new FromRandLeafMStickGenerator(maxImageDimensionDegrees);
		sample = sampleGenerator.getMStick();
	}

	private void tryGenerateMatch() {
		AbstractMStickGenerator matchGenerator = new MetricMorphMStickGenerator(maxImageDimensionDegrees, sample, mmp);
		match = matchGenerator.getMStick();
	}

	private void tryGenerateQualitativeMorphDistractors() {
		for (QualitativeMorphParams qmp:qmps) {
			AbstractMStickGenerator qmGenerator = new QualitativeMorphMStickGenerator(maxImageDimensionDegrees, sample, qmp);
			qualitativeMorphDistractors.add(qmGenerator.getMStick());
		}
	}

	private void tryGenerateRandomDistractors() {
		for(int i=0; i<trialParameters.getNumDistractors().getNumRandDistractors(); i++) {
			AbstractMStickGenerator randGenerator = new RandMStickGenerator(maxImageDimensionDegrees);
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

	
	public Rand<AllenMatchStick> getmSticks() {
		Rand<AllenMatchStick> matchSticks = new Rand<AllenMatchStick>();
		matchSticks.setSample(sample);
		matchSticks.setMatch(match);
		for(AllenMatchStick randDistractor:randDistractors){
			matchSticks.addRandDistractor(randDistractor);
		}
		for(AllenMatchStick qmDistractor:qualitativeMorphDistractors){
			matchSticks.addQualitativeMorphDistractor(qmDistractor);
		}
		return matchSticks;
		
	}
	
	public Rand<AllenMStickSpec> getmStickSpecs() {
		Rand<AllenMStickSpec> specs = new Rand<AllenMStickSpec>();
		specs.setSample(mStickToSpec(sample));
		specs.setMatch(mStickToSpec(match));
		for (AllenMatchStick qmDistractor: qualitativeMorphDistractors) {
			specs.getQualitativeMorphDistractors().add(mStickToSpec(qmDistractor));
		}
		for (AllenMatchStick randDistractor: randDistractors) {
			specs.getRandDistractors().add(mStickToSpec(randDistractor));
		}
		return specs;
	}
	
	private AllenMStickSpec mStickToSpec(AllenMatchStick mStick) {
		AllenMStickSpec spec = new AllenMStickSpec();
		spec.setMStickInfo(mStick);
		return spec;
	}



}
