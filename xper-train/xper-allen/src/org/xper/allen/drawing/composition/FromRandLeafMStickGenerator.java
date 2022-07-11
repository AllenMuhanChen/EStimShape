package org.xper.allen.drawing.composition;

import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;

public class FromRandLeafMStickGenerator extends AbstractMStickGenerator implements MStickGenerator {
	private static final int maxAttemptsToGenerateSeedMStick = 5;
	private static final int maxAttemptsToChooseRandLeaf = 5;
	private static final int maxAttemptsToGenerateMStickFromLeaf = 5;

	private AbstractMStickPngTrialGenerator generator;

	private AllenMatchStick seedMStick;
	public FromRandLeafMStickGenerator(AbstractMStickPngTrialGenerator generator) {
		super();
		this.generator = generator;
	}

	private int seedLeaf;
	
	public void attemptGenerate() {
		try {
			attemptGenerateSeedMatchStick();
			attemptChooseRandLeaf();
			attemptGenerateMStickFromLeaf();
			successful = true;
		} catch (Exception e) {
			successful = false;
		}
	}

	private void attemptGenerateSeedMatchStick() {
		int nTries=0;
		while(nTries<maxAttemptsToGenerateSeedMStick) {
			seedMStick = new AllenMatchStick();
			generator.setProperties(seedMStick);
			try {
				seedMStick.genMatchStickRand();
				break;
			} catch(Exception e) {
				nTries++;
			}
		}

		if(nTries>=maxAttemptsToGenerateSeedMStick) {
			fail("seedMatchStick generation", nTries);
		}

	}

	private void attemptChooseRandLeaf() {
		int nTries=0;
		while(nTries<maxAttemptsToChooseRandLeaf) {
			try {
				seedLeaf = chooseRandLeaf(seedMStick);
				break;
			} catch(Exception e) {
				nTries++;
			}
		}

		if (nTries >= maxAttemptsToChooseRandLeaf)
			fail("chooseRandLeaf", nTries);
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
