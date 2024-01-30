package org.xper.allen.nafc.experiment;

import org.jzy3d.plot3d.rendering.image.GLImage;
import org.lwjgl.opengl.GL11;
import org.xper.Dependency;

import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;

public class ScreenShotter {
    @Dependency
    boolean isEnabled;

    @Dependency
    String directory;

    @Dependency
    int screenHeightPixels;

    @Dependency
    int screenWidthPixels;

    public void takeScreenShot(String filename) {
        if (isEnabled) {
            String path = directory + "/" + filename;
            path=path+".bmp";

            saveImage(path, screenHeightPixels, screenWidthPixels);
        }
    }

    private String saveImage(String path, int height, int width) {
        byte[] data = screenShotBinary(width,height);



        try {
            FileOutputStream fos = new FileOutputStream(path);
            fos.write(data);
            fos.close();
            return path;
        }

        catch (IOException e) {
            e.printStackTrace();
            return "Error: No Path";
        }
    }

    private byte[] screenShotBinary(int width, int height)
    {
        ByteBuffer framebytes = allocBytes(width * height * 3);

        int[] pixels = new int[width * height];
        int bindex;
        // grab a copy of the current frame contents as RGB (has to be UNSIGNED_BYTE or colors come out too dark)
        GL11.glReadPixels(0, 0, width, height, GL11.GL_RGB, GL11.GL_UNSIGNED_BYTE, framebytes);
        // copy RGB data from ByteBuffer to integer array
        for (int i = 0; i < pixels.length; i++) {
            bindex = i * 3;
            pixels[i] =
                             ((framebytes.get(bindex)   & 0x000000FF) << 16)   // R
                            | ((framebytes.get(bindex+1) & 0x000000FF) <<  8)   // G
                            | ((framebytes.get(bindex+2) & 0x000000FF) <<  0);  // B
        }
        // free up this memory
        framebytes = null;
        // flip the pixels vertically (opengl has 0,0 at lower left, java is upper left)
        pixels = GLImage.flipPixels(pixels, width, height);

        try {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_INT_RGB);
            image.setRGB(0, 0, width, height, pixels, 0, width);

            javax.imageio.ImageIO.write(image, "bmp", out);
            byte[] data = out.toByteArray();

            return data;
        }
        catch (Exception e) {
            System.out.println("screenShot(): exception " + e);
            return null;
        }
    }

    private static ByteBuffer allocBytes(int howmany) {
        final int SIZE_BYTE = 3;
        return ByteBuffer.allocateDirect(howmany * SIZE_BYTE).order(ByteOrder.nativeOrder());
    }

    public boolean isEnabled() {
        return isEnabled;
    }

    public void setEnabled(boolean enabled) {
        isEnabled = enabled;
    }

    public String getDirectory() {
        return directory;
    }

    public void setDirectory(String directory) {
        this.directory = directory;
    }

    public int getScreenHeightPixels() {
        return screenHeightPixels;
    }

    public void setScreenHeightPixels(int screenHeightPixels) {
        this.screenHeightPixels = screenHeightPixels;
    }

    public int getScreenWidthPixels() {
        return screenWidthPixels;
    }

    public void setScreenWidthPixels(int screenWidthPixels) {
        this.screenWidthPixels = screenWidthPixels;
    }
}