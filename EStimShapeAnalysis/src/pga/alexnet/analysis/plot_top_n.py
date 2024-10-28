import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageOps
from pathlib import Path
from clat.util.connection import Connection
from src.pga.alexnet import alexnet_context


def plot_stimuli_row(stimuli: list[dict], axes):
    """
    Plot a row of stimuli with colored borders based on response values.

    Parameters:
    stimuli (list): A list of dictionaries, each containing:
     a 'path' key with the path to the image file,
     a 'normalized_response' key with the response value -1-1,
    """
    """Plot a row of stimuli with red borders for positive responses and blue for negative."""
    for i, stim in enumerate(stimuli):
        img_path = Path(stim['path'])
        if img_path.exists():
            img = Image.open(img_path)
            img_with_border = add_colored_border(img, stim['normalized_response'])

            axes[i].imshow(img_with_border)
            axes[i].axis('off')

            # Add text to the top-right corner of the image
            axes[i].text(img_with_border.size[0] - 5, 5,
                         f"Response: {stim['response']:.2f}\nID: {stim['stim_id']}\nLineage: {stim['lineage_id']}",
                         fontsize=5, color='black',
                         transform=axes[i].transData,
                         ha='right', va='top')
        else:
            print(f"Warning: Image not found at {img_path}")
            axes[i].text(0.5, 0.5, f"Image not found\nID: {stim['stim_id']}",
                         ha='center', va='center')
            axes[i].axis('off')


def normalize_responses(stimuli: list[dict]):
    """
    Normalize responses to the range -1 to 1, preserving the original signs and mapping 0 to 0.

    Parameters:
    stimuli (list): A list of dictionaries, each containing a 'response' key with the value to be normalized.

    Mutates the input list by adding a 'normalized_response' key to each dictionary.
    """
    if stimuli[0].keys().__contains__('activation'):
        responses = [stim['activation'] for stim in stimuli]
    else:
        responses = [stim['response'] for stim in stimuli]

    if not responses:
        return []

    # Find the minimum and maximum values for normalization
    min_val = min(responses)
    max_val = max(responses)

    # Handle the case where all responses are 0
    if min_val == 0 and max_val == 0:
        return [0] * len(responses)

    # Normalize the responses while preserving the original signs and mapping 0 to 0

    for i, stim in enumerate(stimuli):
        r = responses[i]    # Original response value
        if r == 0:
            stim['normalized_response'] = 0
        elif r > 0:
            stim['normalized_response'] = r / max_val
        else:
            stim['normalized_response'] = r / abs(min_val)


def add_colored_border(image, normalized_response, border_width=5):
    """Add a colored border to the image based on response value (red for positive, blue for negative)."""
    if normalized_response >= 0:
        border_color = (int(255 * normalized_response), 0, 0)  # Red scale for positive
    else:
        border_color = (0, 0, int(255 * abs(normalized_response)))  # Blue scale for negative
    return ImageOps.expand(image, border=border_width, fill=border_color)


def plot_top_and_bottom_stimuli(n=5, fig_size=(20, 4)):
    """Plot top N positive and negative stimuli with colored borders."""
    conn = alexnet_context.ga_config.connection()

    # Get both positive and negative stimuli
    pos_stimuli = get_top_n_stimuli(conn, n, most_negative=False)
    neg_stimuli = get_top_n_stimuli(conn, n, most_negative=True)
    all_stimuli = pos_stimuli + neg_stimuli
    normalize_responses(all_stimuli)

    # Calculate grid dimensions
    ncols = min(10, n)  # 10 images per row maximum
    nrows = ((n - 1) // 10 + 1) * 2  # Calculate number of rows needed (doubled for pos/neg)

    # Create figure with adjusted height for both positive and negative rows
    fig_height = fig_size[1] * nrows / 2  # Divide by 2 since we doubled nrows
    fig, axes = plt.subplots(nrows, ncols, figsize=(fig_size[0], fig_height))

    # Convert axes to 2D array if it's 1D
    if len(axes.shape) == 1:
        axes = axes.reshape(2, -1)

    # Plot positive responses in top rows
    pos_axes = axes[:(nrows // 2)].flatten()
    plot_stimuli_row(pos_stimuli, pos_axes)

    # Plot negative responses in bottom rows
    neg_axes = axes[(nrows // 2):].flatten()
    plot_stimuli_row(neg_stimuli, neg_axes)

    # Turn off any unused subplots
    for ax_row in axes:
        for ax in ax_row[len(pos_stimuli):]:
            ax.axis('off')

    plt.tight_layout()
    return fig


def get_top_n_stimuli(conn: Connection, n: int, most_negative=False):
    """Get top N stimuli based on response."""
    query = """
    SELECT s.stim_id, s.response, sp.path, s.lineage_id
    FROM StimGaInfo s
    JOIN StimPath sp ON s.stim_id = sp.stim_id
    WHERE s.response IS NOT NULL
    ORDER BY s.response {} 
    LIMIT %s
    """.format('ASC' if most_negative else 'DESC')

    conn.execute(query, (n,))
    results = conn.fetch_all()
    return [{'stim_id': r[0], 'response': r[1], 'path': r[2], 'lineage_id': r[3]} for r in results]


if __name__ == "__main__":
    fig = plot_top_and_bottom_stimuli(n=20)
    plt.show()
