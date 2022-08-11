package org.xper.sach.util;

public class ComplexMatrix {
	private final int nx;
	private final int ny;
    private final double[][] real;
    private final double[][] imag;
    private final double[][] magn;
    private final double[][] phas;
    

    // create a new object with the given real and imaginary parts
    public ComplexMatrix(int nx, int ny, double[][] realimag) {
    	this.nx = nx;
        this.ny = ny;
        
        this.real = new double[nx][ny];
        this.imag = new double[nx][ny];
        
        this.magn = new double[nx][ny];
        this.phas = new double[nx][ny];
        
        splitRealImag(realimag);
        genEuler();
    }
    
 // create a new object with the given magnitude and phase
    public ComplexMatrix(int nx, int ny, double[][] magn, double[][] phas) {
    	this.nx = nx;
        this.ny = ny;
        
    	this.magn = magn;
        this.phas = phas;
        
        this.real = new double[nx][ny];
        this.imag = new double[nx][ny];
        
    	genCart();
    }

    private void genEuler() {
    	for (int i=0; i<nx; i++) {
    		for (int j=0; j<ny; j++) {
    			magn[i][j] = Math.sqrt(real[i][j]*real[i][j] + real[i][j]*real[i][j]);
    			phas[i][j] = Math.atan2(imag[i][j], real[i][j]);
    		}
    	}
    }
    
    private void genCart() {
    	for (int i=0; i<nx; i++) {
    		for (int j=0; j<ny; j++) {
    			real[i][j] = magn[i][j]*Math.cos(phas[i][j]);
    			imag[i][j] = magn[i][j]*Math.sin(phas[i][j]);
    		}
    	}
    }
    
    private void splitRealImag(double[][] realimag) {
    	for (int i=0; i<nx; i++) {
    		for (int j=0; j<ny; j+=2) {
    			real[i][j] = realimag[i][j];
    			imag[i][j] = realimag[i][j+1];
    		}
    	}
    }

    public double[][] getMagnitude() {
    	return magn;
    }
    public double[][] getPhase() {
    	return phas;
    }

	public void addPhase(double[][] phase) {
		for (int i=0; i<nx; i++) {
    		for (int j=0; j<ny; j++) {
    			phas[i][j] += phase[i][j];
    		}
    	}
		genCart();
	}

	public double[][] getRealImag() {
		double[][] realimag = new double[nx][ny*2];
		for (int i=0; i<nx; i++) {
    		for (int j=0; j<ny; j+=2) {
    			realimag[i][j] = real[i][j];
    			realimag[i][j+1] = 0;
    		}
    	}
		return realimag;
	}
}