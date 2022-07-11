package org.xper.allen.drawing.composition.qualitativemorphs;

import org.xper.allen.drawing.composition.AbstractMStickGenerator;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.MStickGenerationException;
import org.xper.allen.drawing.composition.MStickGenerator;
import org.xper.allen.drawing.composition.MStickVettingException;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;

public class QualitativeMorphMStickGenerator extends AbstractMStickGenerator{
	private static final int maxAttemptsToGenerateQualitativeMorph = 5;

	private AbstractMStickPngTrialGenerator generator;
	private AllenMatchStick mStickToMorph;
	private QualitativeMorphParams qmp;

	public QualitativeMorphMStickGenerator(AbstractMStickPngTrialGenerator generator, AllenMatchStick mStickToMorph,
			QualitativeMorphParams qmp) {
		super();
		this.generator = generator;
		this.mStickToMorph = mStickToMorph;
		this.qmp = qmp;
	}

	private int leafToMorph;

	@Override
	public void attemptGenerate() {
		int nTries = 0;

		while (nTries<maxAttemptsToGenerateQualitativeMorph) {
			try {
				trySetLeafToMorph();
				tryGenerateQualitativeMorph();
				successful = true;
				break;
			} catch (Exception e) {
				nTries++;
				successful=false;
			}
		}

		if (nTries>=maxAttemptsToGenerateQualitativeMorph) {
			fail("Qualitative Morph generation", nTries);
		}

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
