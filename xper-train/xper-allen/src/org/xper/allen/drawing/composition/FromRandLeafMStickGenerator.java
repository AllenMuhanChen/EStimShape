package org.xper.allen.drawing.composition;

import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;

public class FromRandLeafMStickGenerator extends AbstractMStickGenerator{
	private static final int maxAttemptsToGenerateMStickFromLeaf = 5;


	private AllenMatchStick seedMStick;
	public FromRandLeafMStickGenerator(AbstractMStickPngTrialGenerator generator) {
		super();
		this.generator = generator;
		this.makeAttemptsToGenerate();
	}

	private int seedLeaf;

	protected void attemptToGenerate() {
		attemptGenerateSeedMatchStick();
		attemptChooseRandLeaf();
		attemptGenerateMStickFromLeaf();
	}

	private void attemptGenerateSeedMatchStick() {
		seedMStick = new AllenMatchStick();
		generator.setProperties(seedMStick);
		try {
			seedMStick.genMatchStickRand();
		} catch(Exception e) {
			throw new MStickGenerationException();
		}


	}

	private void attemptChooseRandLeaf() {

		try {
			seedLeaf = chooseRandLeaf(seedMStick);

		} catch(Exception e) {
			throw new MStickVettingException();
		}

	}

	private int chooseRandLeaf(AllenMatchStick baseMStick) {
		int randomLeaf = baseMStick.chooseRandLeaf();
		boolean leafVetSuccess = baseMStick.vetLeaf(randomLeaf);

		if(leafVetSuccess)
			return randomLeaf;
		else
			throw new MStickVettingException();
	}

	private void attemptGenerateMStickFromLeaf() {
		int nTries = 0;
		while(nTries<maxAttemptsToGenerateMStickFromLeaf) {
			try {
				generateMStickFromLeaf();
				break;
			} catch (Exception e) {
				nTries++;
			}
		}

		if(nTries >= maxAttemptsToGenerateMStickFromLeaf)
			fail("generate mStick from leaf", nTries);
	}

	private void generateMStickFromLeaf() {
		mStick = new AllenMatchStick();
		generator.setProperties(mStick);
		boolean success = mStick.genMatchStickFromLeaf(seedLeaf, seedMStick);

		if(!success) {
			throw new MStickGenerationException();
		}
	}



}
