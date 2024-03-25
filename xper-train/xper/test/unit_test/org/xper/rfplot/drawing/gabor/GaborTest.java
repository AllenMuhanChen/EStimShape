package org.xper.rfplot.drawing.gabor;

import org.junit.Test;
import org.xper.util.MathUtil;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.File;
import java.nio.ByteBuffer;

import static org.junit.Assert.*;
//import static org.xper.rfplot.drawing.gabor.Gabor.makeTexture;

//public class GaborTest {
//
//
//
//    public static void main(String[] args) {
//        try {
//            int width = 1000;
//            int height = 1500;
//            double stdDev = 0.2;
//
//            ByteBuffer texture = makeTexture(width, height, stdDev);
//            BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_INT_RGB);
//
//            for (int y = 0; y < height; y++) {
//                for (int x = 0; x < width; x++) {
//                    float value = texture.getFloat((y * width + x) * 4); // Each float is 4 bytes
//                    int rgbValue = (int) (255 * value);
//                    int rgb = (rgbValue << 16) | (rgbValue << 8) | rgbValue;
//                    image.setRGB(x, y, rgb);
//                }
//            }
//
//            File outputFile = new File("texture.png");
//            ImageIO.write(image, "PNG", outputFile);
//            System.out.println("Texture image saved as texture.png");
//        } catch (Exception e) {
//            e.printStackTrace();
//        }
//    }
//}