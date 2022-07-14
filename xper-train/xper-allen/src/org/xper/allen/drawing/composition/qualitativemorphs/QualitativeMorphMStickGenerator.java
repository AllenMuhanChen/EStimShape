package org.xper.allen.drawing.composition.qualitativemorphs;

import org.xper.allen.drawing.composition.AbstractMStickGenerator;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.MStickGenerationException;
import org.xper.allen.drawing.composition.MStickGenerator;
import org.xper.allen.drawing.composition.MStickVettingException;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;

public class QualitativeMorphMStickGenerator extends AbstractMStickGenerator{
	private AllenMatchStick mStickToMorph;
	private QualitativeMorphParams qmp;

	public QualitativeMorphMStickGenerator(AbstractMStickPngTrialGenerator generator, AllenMatchStick mStickToMorph,
			QualitativeMorphParams qmp) {
		super();
		this.generator = generator;
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
		generator.setProperties(mStick);
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
