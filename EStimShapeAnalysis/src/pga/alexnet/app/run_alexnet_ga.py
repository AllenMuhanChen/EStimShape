import os
import subprocess

from src.pga.alexnet import alexnet_context


def main():
    r, g, b = prompt_rgb_values()
    ga = alexnet_context.ga_config.make_genetic_algorithm()
    ga.trial_generator.set_color(r, g, b)

    while ga.gen_id < 20:
        ga.run()



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
