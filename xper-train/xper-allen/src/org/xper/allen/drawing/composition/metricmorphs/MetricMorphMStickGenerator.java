package org.xper.allen.drawing.composition.metricmorphs;

import org.xper.allen.drawing.composition.AbstractMStickGenerator;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.MStickGenerationException;
import org.xper.allen.drawing.composition.MStickVettingException;

public class MetricMorphMStickGenerator extends AbstractMStickGenerator{

	private final AllenMatchStick mStickToMorph;
	private final MetricMorphParams mmp;


	public MetricMorphMStickGenerator(double maxImageDimensionDegrres, AllenMatchStick targetMStick,
									  MetricMorphParams mmp) {
		super(maxImageDimensionDegrres);
		this.mStickToMorph = targetMStick;
		this.mmp = mmp;
		makeAttemptsToGenerate();
	}


	private int leafToMorph;

	@Override
	protected void attemptToGenerate() {
		trySetLeafToMorph();
		tryGenerateMetricMorph();
	}


	private void trySetLeafToMorph() {
		leafToMorph = mStickToMorph.getSpecialEndComp().get(0);
		if(leafToMorph<1) {
			throw new MStickVettingException();
		}
	}

	private void tryGenerateMetricMorph() {
		mStick = new AllenMatchStick();
		mStick.setProperties(maxImageDimensionDegrees, "SHADE");
		boolean success = mStick.genMetricMorphedLeafMatchStick(leafToMorph, mStickToMorph, mmp);

		if(!success) {
			throw new MStickGenerationException();
		}
	}



}