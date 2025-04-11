import os
import subprocess
from time import sleep

from src.pga.alexnet import alexnet_context
from src.pga.alexnet.lighting_posthoc import lighting_test, extract_contributions


def main():
    r, g, b = prompt_rgb_values()


    while True:
        ga = alexnet_context.ga_config.make_genetic_algorithm()
        ga.trial_generator.set_color(r, g, b)
        ga.run(,
        sleep(5)
        print("Gen ID: ", ga.gen_id)
        if ga.gen_id >= 80:
            break

    lighting_test.main()
    extract_contributions.main()


def prompt_rgb_values():
    while True:
        rgb_input = input("Please enter RGB values in the format R,G,B (each between 0 and 255): ")
        try:
            r, g, b = map(int, rgb_input.split(','))
            if all(0 <= value <= 255 for value in [r, g, b]):
                return r, g, b
            else:
                print("Values must be between 0 and 255. Please try again.")
        except ValueError:
            print("Invalid format. Please ensure you enter three comma-separated numbers.")


if __name__ == "__main__":
    main()
