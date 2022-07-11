package org.xper.allen.drawing.composition.metricmorphs;

import org.xper.allen.drawing.composition.AbstractMStickGenerator;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.MStickGenerationException;
import org.xper.allen.drawing.composition.MStickGenerator;
import org.xper.allen.drawing.composition.MStickVettingException;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;

public class MetricMorphMStickGenerator extends AbstractMStickGenerator{
	private static final int maxAttemptsToGenerateMetricMorph = 5;

	private AbstractMStickPngTrialGenerator generator;
	private AllenMatchStick mStickToMorph;

	private MetricMorphParams mmp;


	public MetricMorphMStickGenerator(AbstractMStickPngTrialGenerator generator, AllenMatchStick targetMStick,
			MetricMorphParams mmp) {
		super();
		this.generator = generator;
		this.mStickToMorph = targetMStick;
		this.mmp = mmp;
	}

	private int leafToMorph;

	public void attemptGenerate() {
		int nTries=0;
		while(nTries<maxAttemptsToGenerateMetricMorph) {
			try {
				trySetLeafToMorph();
				tryGenerateMetricMorph();
				successful=true;
				break;
			} catch (Exception e) {
				nTries++;
				successful=false;
			}
		}

		if(nTries>maxAttemptsToGenerateMetricMorph) {
			fail("MetricMorph Generation", nTries);
		}
	}

	private void trySetLeafToMorph() {
		leafToMorph = mStickToMorph.getSpecialEndComp().get(0);
		if(leafToMorph<1) {
			throw new MStickVettingException();
		}
	}

	private void tryGenerateMetricMorph() {
		mStick = new AllenMatchStick();
		generator.setProperties(mStick);
		boolean success = mStick.genMetricMorphedLeafMatchStick(leafToMorph, mStickToMorph, mmp);

		if(!success) {
			throw new MStickGenerationException();
		}
	}

}
