package org.xper.allen.drawing;

import javax.imageio.IIOImage;
import javax.imageio.ImageIO;
import javax.imageio.ImageWriteParam;
import javax.imageio.ImageWriter;
import javax.imageio.stream.ImageOutputStream;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.Iterator;
import java.util.List;

public class MJPEGCreator {

    public static void createMJPEG(List<BufferedImage> frames, String outputFile, float quality) throws IOException {
        try (FileOutputStream fos = new FileOutputStream(outputFile);
             ImageOutputStream ios = ImageIO.createImageOutputStream(fos)) {

            Iterator<ImageWriter> writers = ImageIO.getImageWritersByFormatName("jpeg");
            ImageWriter writer = writers.next();

            writer.setOutput(ios);

            ImageWriteParam param = writer.getDefaultWriteParam();
            param.setCompressionMode(ImageWriteParam.MODE_EXPLICIT);
            param.setCompressionQuality(quality); // Change the quality here, 1.0f is the highest

            writer.prepareWriteSequence(null);

            for (BufferedImage frame : frames) {
                // Convert to a type that's compatible with JPEG
                BufferedImage imageToWrite = new BufferedImage(frame.getWidth(), frame.getHeight(), BufferedImage.TYPE_INT_RGB);
                Graphics2D g = imageToWrite.createGraphics();
                g.drawImage(frame, 0, 0, null);
                g.dispose();

                // Write the image as a JPEG
                IIOImage iioImage = new IIOImage(imageToWrite, null, null);
                writer.writeToSequence(iioImage, param);
            }

            writer.endWriteSequence();
        }
    }

    private static byte[] intToBytes(int value) {
        return new byte[] {
                (byte)(value >>> 24),
                (byte)(value >>> 16),
                (byte)(value >>> 8),
                (byte)value};
    }


}