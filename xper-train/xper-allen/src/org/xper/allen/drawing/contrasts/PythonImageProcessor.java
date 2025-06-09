package org.xper.allen.drawing.contrasts;

import java.io.*;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.concurrent.TimeUnit;
import java.util.UUID;

/**
 * Java wrapper for Python image processing script.
 * Handles CIELAB-based colormapping of images via direct process execution.
 */
public class PythonImageProcessor {

    private final String pythonScriptPath;
    private final String pythonExecutable;
    private final int timeoutSeconds;

    /**
     * Constructor with default settings.
     *
     * @param pythonScriptPath Path to the process_image.py script
     */
    public PythonImageProcessor(String pythonScriptPath) {
        this(pythonScriptPath, "python3", 60);
    }

    /**
     * Constructor with custom settings.
     *
     * @param pythonScriptPath Path to the process_image.py script
     * @param pythonExecutable Python executable command (e.g., "python3", "python", or path to venv python)
     * @param timeoutSeconds   Timeout for Python process execution
     */
    public PythonImageProcessor(String pythonScriptPath, String pythonExecutable, int timeoutSeconds) {
        this.pythonScriptPath = pythonScriptPath;
        this.pythonExecutable = pythonExecutable;
        this.timeoutSeconds = timeoutSeconds;

        // Validate that the Python script exists
        if (!Files.exists(Paths.get(pythonScriptPath))) {
            throw new IllegalArgumentException("Python script not found: " + pythonScriptPath);
        }

        // Validate Python executable exists (if it's a path)
        if (pythonExecutable.contains("/") && !Files.exists(Paths.get(pythonExecutable))) {
            throw new IllegalArgumentException("Python executable not found: " + pythonExecutable);
        }
    }

    /**
     * Constructor for use with virtual environment.
     *
     * @param pythonScriptPath Path to the process_image.py script
     * @param venvPath Path to virtual environment (will use venv/bin/python)
     */
    public static PythonImageProcessor withVirtualEnv(String pythonScriptPath, String venvPath) {
        String pythonExecutable = Paths.get(venvPath, "bin", "python").toString();
        return new PythonImageProcessor(pythonScriptPath, pythonExecutable, 60);
    }

    /**
     * Process an image with default output path and default label.
     *
     * @param inputImagePath Path to input image
     * @return File object pointing to the processed image
     * @throws IOException If file operations fail
     * @throws InterruptedException If process is interrupted
     * @throws ImageProcessingException If Python script fails
     */
    public File processImage(String inputImagePath) throws IOException, InterruptedException, ImageProcessingException {
        return processImage(inputImagePath, "processed");
    }

    /**
     * Process an image with default output path and custom label.
     *
     * @param inputImagePath Path to input image
     * @param label Label to include in output filename
     * @return File object pointing to the processed image
     * @throws IOException If file operations fail
     * @throws InterruptedException If process is interrupted
     * @throws ImageProcessingException If Python script fails
     */
    public File processImage(String inputImagePath, String label) throws IOException, InterruptedException, ImageProcessingException {
        // Generate unique output filename with label
        String outputPath = generateOutputPath(inputImagePath, label);
        return processImage(inputImagePath, outputPath, false);
    }

    /**
     * Process an image with custom label and keepIntermediates option.
     *
     * @param inputImagePath Path to input image
     * @param keepIntermediates Whether to save intermediate processing files
     * @param label Label to include in output filename
     * @return File object pointing to the processed image
     * @throws IOException If file operations fail
     * @throws InterruptedException If process is interrupted
     * @throws ImageProcessingException If Python script fails
     */
    public File processImage(String inputImagePath, boolean keepIntermediates, String label)
            throws IOException, InterruptedException, ImageProcessingException {
        // Generate unique output filename with label
        String outputPath = generateOutputPath(inputImagePath, label);
        return processImage(inputImagePath, outputPath, keepIntermediates);
    }

    /**
     * Process an image with specified output path.
     *
     * @param inputImagePath Path to input image
     * @param outputImagePath Path for output image
     * @param keepIntermediates Whether to save intermediate processing files
     * @return File object pointing to the processed image
     * @throws IOException If file operations fail
     * @throws InterruptedException If process is interrupted
     * @throws ImageProcessingException If Python script fails
     */
    public File processImage(String inputImagePath, String outputImagePath, boolean keepIntermediates)
            throws IOException, InterruptedException, ImageProcessingException {

        // Validate input file exists
        Path inputPath = Paths.get(inputImagePath);
        if (!Files.exists(inputPath)) {
            throw new FileNotFoundException("Input image not found: " + inputImagePath);
        }

        // Create output directory if needed
        Path outputPath = Paths.get(outputImagePath);
        Path outputDir = outputPath.getParent();
        if (outputDir != null && !Files.exists(outputDir)) {
            Files.createDirectories(outputDir);
        }

        // Build command
        ProcessBuilder pb = new ProcessBuilder();
        if (keepIntermediates) {
            pb.command(pythonExecutable, pythonScriptPath, inputImagePath, outputImagePath, "--keep-intermediates");
        } else {
            pb.command(pythonExecutable, pythonScriptPath, inputImagePath, outputImagePath);
        }

        pb.redirectErrorStream(true);

        // Execute process
        Process process = pb.start();

        // Capture output
        StringBuilder output = new StringBuilder();
        StringBuilder errors = new StringBuilder();

        try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
            String line;
            while ((line = reader.readLine()) != null) {
                if (line.startsWith("ERROR:") || line.startsWith("FAILED:")) {
                    errors.append(line).append("\n");
                } else {
                    output.append(line).append("\n");
                }
            }
        }

        // Wait for completion with timeout
        boolean finished = process.waitFor(timeoutSeconds, TimeUnit.SECONDS);
        if (!finished) {
            process.destroyForcibly();
            throw new ImageProcessingException("Python process timed out after " + timeoutSeconds + " seconds");
        }

        // Check exit code
        int exitCode = process.exitValue();
        if (exitCode != 0) {
            String errorMessage = errors.length() > 0 ? errors.toString() : output.toString();
            throw new ImageProcessingException("Python process failed with exit code " + exitCode + ": " + errorMessage);
        }

        // Verify output file was created
        if (!Files.exists(outputPath)) {
            throw new ImageProcessingException("Output file was not created: " + outputImagePath);
        }

        return outputPath.toFile();
    }

    /**
     * Generate a unique output path based on input path and label.
     * Format: {original_filename}_{label}.png
     *
     * @param inputPath Path to input image
     * @param label Label to include in filename
     * @return Generated output path
     */
    private String generateOutputPath(String inputPath, String label) {
        Path input = Paths.get(inputPath);
        String fileName = input.getFileName().toString();

        // Extract base name without extension
        String baseName;
        int lastDotIndex = fileName.lastIndexOf('.');
        if (lastDotIndex > 0) {
            baseName = fileName.substring(0, lastDotIndex);
        } else {
            baseName = fileName;
        }

        // Clean the label to make it filesystem-safe
        String cleanLabel = label.replaceAll("[^a-zA-Z0-9_-]", "_");

        // Create new filename: {original_filename}_{label}.png
        String newFileName = baseName + "_" + cleanLabel + ".png";

        return input.getParent().resolve(newFileName).toString();
    }

    /**
     * Legacy method - Generate a unique output path based on input path.
     * @deprecated Use {@link #generateOutputPath(String, String)} instead
     */
    @Deprecated
    private String generateOutputPath(String inputPath) {
        return generateOutputPath(inputPath, "processed_" + UUID.randomUUID().toString().substring(0, 8));
    }

    /**
     * Custom exception for image processing errors.
     */
    public static class ImageProcessingException extends Exception {
        public ImageProcessingException(String message) {
            super(message);
        }

        public ImageProcessingException(String message, Throwable cause) {
            super(message, cause);
        }
    }

    /**
     * Example usage and testing.
     */
    public static void main(String[] args) {
        if (args.length < 2) {
            System.err.println("Usage: java PythonImageProcessor <python_script_path> <input_image_path> [label]");
            System.exit(1);
        }

        String scriptPath = args[0];
        String inputImagePath = args[1];
        String label = args.length > 2 ? args[2] : "example";

        try {
            // Example using virtual environment
            PythonImageProcessor processor = PythonImageProcessor.withVirtualEnv(scriptPath, "/home/r2_allen/anaconda3/envs/3.11");

            // Example using default python3
            // PythonImageProcessor processor = new PythonImageProcessor(scriptPath);

            File outputFile = processor.processImage(inputImagePath, label);
            System.out.println("Image processed successfully: " + outputFile.getAbsolutePath());

        } catch (Exception e) {
            System.err.println("Failed to process image: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        }
    }
}