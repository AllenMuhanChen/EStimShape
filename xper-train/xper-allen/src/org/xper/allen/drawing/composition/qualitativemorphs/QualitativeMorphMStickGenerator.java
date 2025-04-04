package org.xper.allen.drawing.composition.qualitativemorphs;

import org.xper.allen.drawing.composition.AbstractMStickGenerator;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.MStickGenerationException;
import org.xper.allen.drawing.composition.MStickVettingException;

public class QualitativeMorphMStickGenerator extends AbstractMStickGenerator{
	private AllenMatchStick mStickToMorph;
	private QualitativeMorphParams qmp;


	public QualitativeMorphMStickGenerator(double maxImageDimensionDegrees, AllenMatchStick mStickToMorph, QualitativeMorphParams qmp) {
		super(maxImageDimensionDegrees);
		this.mStickToMorph = mStickToMorph;
		this.qmp = qmp;

		makeAttemptsToGenerate();
	}

	private int leafToMorph;

	@Override
	protected void attemptToGenerate() {
		trySetLeafToMorph();
		tryGenerateQualitativeMorph();
	}

	private void trySetLeafToMorph() {
		leafToMorph = mStickToMorph.getSpecialEndComp().get(0);
		if(leafToMorph<1) {
			throw new MStickVettingException();
		}
	}

	private void tryGenerateQualitativeMorph() {
		mStick = new AllenMatchStick();
		mStick.setProperties(maxImageDimensionDegrees, "SHADE", 1.0);
		boolean success = false;
		try {
			success = mStick.genQualitativeMorphedLeafMatchStick(leafToMorph, mStickToMorph, qmp);
		}
		catch (Exception e) {
			e.printStackTrace();
		}
		if(!success) {
			throw new MStickGenerationException();
		}
		}


	}