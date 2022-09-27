package org.xper.allen.nafc.blockgen;

import org.xper.png.ImageDimensions;
import org.xper.allen.specs.NoisyPngSpec;
import org.xper.drawing.Coordinates2D;

public class NoisyPngSpecWriter{

	static public NoisyPngSpecWriter createWithNoiseMap(
			Coordinates2D coords,
			String pngPath,
			String noiseMapPath,
			ImageDimensions pngDimensions) {
		return new NoisyPngSpecWriter(coords, pngPath, noiseMapPath, pngDimensions);
	}
	
	static public NoisyPngSpecWriter createWithNoiseMap(
			Coordinates2D coords,
			String pngPath,
			String noiseMapPath,
			double pngDimension) {
		ImageDimensions pngDimensions = new ImageDimensions(pngDimension, pngDimension);
		return new NoisyPngSpecWriter(coords, pngPath, noiseMapPath, pngDimensions);
	}

	static public NoisyPngSpecWriter createWithoutNoiseMap(
			Coordinates2D coords,
			String pngPath,
			ImageDimensions pngDimensions) {
		return new NoisyPngSpecWriter(coords, pngPath, pngDimensions);
	}
	
	static public NoisyPngSpecWriter createWithoutNoiseMap(
			Coordinates2D coords,
			String pngPath,
			double pngDimension) {
		ImageDimensions pngDimensions = new ImageDimensions(pngDimension, pngDimension);
		return new NoisyPngSpecWriter(coords, pngPath, pngDimensions);
	}

	private NoisyPngSpecWriter(Coordinates2D coords, String pngPath, String noiseMapPath,
			ImageDimensions pngDimensions) {
		super();
		this.coords = coords;
		this.pngPath = pngPath;
		this.noiseMapPath = noiseMapPath;
		this.pngDimensions = pngDimensions;
	}

	private NoisyPngSpecWriter(Coordinates2D coords, String pngPath,
			ImageDimensions pngDimensions) {
		super();
		this.coords = coords;
		this.pngPath = pngPath;
		this.pngDimensions = pngDimensions;
	}

	
	public NoisyPngSpecWriter() {}

	NoisyPngSpec spec = new NoisyPngSpec();

	public void writeSpec() {
		setCoords();
		setPngPath();
		setNoiseMapPath();
		setImageDimensions();
	}

	Coordinates2D coords;
	protected void setCoords() {
		spec.setxCenter(coords.getX());
		spec.setyCenter(coords.getY());
	}

	String pngPath;
	protected void setPngPath() {
		spec.setPngPath(pngPath);
	}

	String noiseMapPath;
	protected void setNoiseMapPath() {
		if(noiseMapPath != null)
			spec.setNoiseMapPath(noiseMapPath);
		else
			spec.setNoiseMapPath("");
	}

	ImageDimensions pngDimensions;
	protected void setImageDimensions() {
		spec.setImageDimensions(pngDimensions);
	}

	public NoisyPngSpec getSpec() {
		return spec;
	}
}
