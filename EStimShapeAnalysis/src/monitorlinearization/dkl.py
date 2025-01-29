import logging

import numpy


def dkl2rgb(dkl, conversionMatrix=None):
    """Convert from DKL color space (Derrington, Krauskopf & Lennie) to RGB.

    Requires a conversion matrix, which will be generated from generic
    Sony Trinitron phosphors if not supplied (note that this will not be
    an accurate representation of the color space unless you supply a
    conversion matrix).

    Examples
    --------
    Converting a single DKL color to RGB::

        dkl = [90, 0, 1]
        rgb = dkl2rgb(dkl, conversionMatrix)

    """
    # make sure the input is an array
    dkl = numpy.asarray(dkl)

    if conversionMatrix is None:
        conversionMatrix = numpy.asarray([
            # (note that dkl has to be in cartesian coords first!)
            # LUMIN    %L-M    %L+M-S
            [1.0000, 1.0000, -0.1462],  # R
            [1.0000, -0.3900, 0.2094],  # G
            [1.0000, 0.0180, -1.0000]])  # B
        logging.warning('This monitor has not been color-calibrated. '
                        'Using default DKL conversion matrix.')

    if len(dkl.shape) == 3:
        dkl_NxNx3 = dkl
        # convert a 2D (image) of Spherical DKL colours to RGB space
        origShape = dkl_NxNx3.shape  # remember for later
        NxN = origShape[0] * origShape[1]  # find nPixels
        dkl = numpy.reshape(dkl_NxNx3, [NxN, 3])  # make Nx3
        rgb = dkl2rgb(dkl, conversionMatrix)  # convert
        return numpy.reshape(rgb, origShape)  # reshape and return

    else:
        dkl_Nx3 = dkl
        # its easier to use in the other orientation!
        dkl_3xN = numpy.transpose(dkl_Nx3)
        if numpy.size(dkl_3xN) == 3:
            RG, BY, LUM = sph2cart(dkl_3xN[0],
                                   dkl_3xN[1],
                                   dkl_3xN[2])
        else:
            RG, BY, LUM = sph2cart(dkl_3xN[0, :],
                                   dkl_3xN[1, :],
                                   dkl_3xN[2, :])
        dkl_cartesian = numpy.asarray([LUM, RG, BY])
        rgb = numpy.dot(conversionMatrix, dkl_cartesian)

        # return in the shape we received it:
        return numpy.transpose(rgb)

def rgb2dklCart(picture, conversionMatrix=None):
    """Convert an RGB image into Cartesian DKL space.
    """
    # Turn the picture into an array so we can do maths
    picture = numpy.array(picture)
    # Find the original dimensions of the picture
    origShape = picture.shape

    # this is the inversion of the dkl2rgb conversion matrix
    if conversionMatrix is None:
        conversionMatrix = numpy.asarray([
            # LUMIN->    %L-M->        L+M-S
            [0.25145542, 0.64933633, 0.09920825],
            [0.78737943, -0.55586618, -0.23151325],
            [0.26562825, 0.63933074, -0.90495899]])
        logging.warning('This monitor has not been color-calibrated. '
                        'Using default DKL conversion matrix.')
    else:
        conversionMatrix = numpy.linalg.inv(conversionMatrix)

    # Reshape the picture so that it can multiplied by the conversion matrix
    red = picture[:, :, 0]
    green = picture[:, :, 1]
    blue = picture[:, :, 2]

    dkl = numpy.asarray([red.reshape([-1]),
                         green.reshape([-1]),
                         blue.reshape([-1])])

    # Multiply the picture by the conversion matrix
    dkl = numpy.dot(conversionMatrix, dkl)

    # Reshape the picture so that it's back to it's original shape
    dklPicture = numpy.reshape(numpy.transpose(dkl), origShape)

    return dklPicture

def sph2cart(*args):
    """Convert from spherical coordinates (elevation, azimuth, radius)
    to cartesian (x,y,z).

    usage:
        array3xN[x,y,z] = sph2cart(array3xN[el,az,rad])
        OR
        x,y,z = sph2cart(elev, azim, radius)
    """
    if len(args) == 1:  # received an Nx3 array
        elev = args[0][0, :]
        azim = args[0][1, :]
        radius = args[0][2, :]
        returnAsArray = True
    elif len(args) == 3:
        elev = args[0]
        azim = args[1]
        radius = args[2]
        returnAsArray = False

    z = radius * numpy.sin(numpy.radians(elev))
    x = radius * numpy.cos(numpy.radians(elev)) * numpy.cos(numpy.radians(azim))
    y = radius * numpy.cos(numpy.radians(elev)) * numpy.sin(numpy.radians(azim))
    if returnAsArray:
        return numpy.asarray([x, y, z])
    else:
        return x, y, z


import numpy as np
import time


def get_conversion_matrix_script():
    """
    Interactive script to collect colorimeter measurements and generate a DKL conversion matrix.
    Returns the conversion matrix based on user input measurements.
    """
    measurements = {}
    print("\nDKL Conversion Matrix Generation Script")
    print("======================================")

    input("\nPress Enter when ready to begin measurements...")

    # Function to get XYZ values with validation
    def get_xyz_values(color_name, rgb_values):
        while True:
            print(f"\nSet your display to RGB{rgb_values}")
            input(f"Press Enter when ready to measure {color_name}...")
            print(f"\nEnter XYZ values for {color_name}:")
            try:
                x = float(input("X value: "))
                y = float(input("Y value: "))
                z = float(input("Z value: "))
                # Basic validation
                if all(0 <= val <= 1 for val in [x, y, z]):
                    return [x, y, z]
                else:
                    print("\nError: Values should be between 0 and 1. Please try again.")
            except ValueError:
                print("\nError: Please enter valid numbers.")

    # Collect measurements for each primary color
    primaries = {
        'R': (255, 0, 0),
        'G': (0, 255, 0),
        'B': (0, 0, 255)
    }

    for color, rgb in primaries.items():
        print(f"\n{'-' * 50}")
        print(f"Measuring {color} primary")
        measurements[color] = get_xyz_values(color, rgb)
        time.sleep(1)  # Give time between measurements

    # Also measure black and white points
    print(f"\n{'-' * 50}")
    measurements['BLACK'] = get_xyz_values("black point", (0, 0, 0))
    print(f"\n{'-' * 50}")
    measurements['WHITE'] = get_xyz_values("white point", (255, 255, 255))

    # Create conversion matrix
    xyz_to_lms = np.array([
        [0.38971, 0.68898, -0.07868],
        [-0.22981, 1.18340, 0.04641],
        [0.00000, 0.00000, 1.00000]
    ])

    # Create matrix of RGB primary responses in LMS space
    rgb_lms = np.zeros((3, 3))
    for i, primary in enumerate(['R', 'G', 'B']):
        xyz = np.array(measurements[primary])
        rgb_lms[:, i] = np.dot(xyz_to_lms, xyz)

    # Normalize to white point
    white_lms = np.sum(rgb_lms, axis=1)
    rgb_lms = rgb_lms / white_lms[:, np.newaxis]

    # Create DKL isolation matrix
    dkl_matrix = np.array([
        [1, 1, 0],  # L+M (luminance)
        [1, -1, 0],  # L-M (red-green)
        [-1, -1, 1]  # S-(L+M) (blue-yellow)
    ])

    # Calculate final conversion matrix
    conversion_matrix = np.linalg.solve(dkl_matrix @ rgb_lms, np.eye(3))

    # Save measurements and matrix
    np.save('colorimeter_measurements.npy', measurements)
    np.save('dkl_conversion_matrix.npy', conversion_matrix)

    print("\nMeasurements complete!")
    print("Saved measurements to 'colorimeter_measurements.npy'")
    print("Saved conversion matrix to 'dkl_conversion_matrix.npy'")

    return conversion_matrix


def main():
    """
    Main function to run the colorimeter measurement script and test the resulting matrix.
    """
    print("Welcome to the DKL Conversion Matrix Generator")
    print("============================================")

    try:
        conversion_matrix = get_conversion_matrix_script()

        # Test the matrix with a simple DKL value
        test_dkl = np.array([90, 0, 1])
        rgb = dkl2rgb(test_dkl, conversion_matrix)

        print("\nTest Results:")
        print("--------------")
        print(f"Test DKL value: {test_dkl}")
        print(f"Converted RGB: {rgb}")

    except KeyboardInterrupt:
        print("\n\nMeasurement process interrupted.")
        print("No conversion matrix was generated.")
    except Exception as e:
        print(f"\n\nAn error occurred: {str(e)}")
        print("No conversion matrix was generated.")


if __name__ == '__main__':
    main()