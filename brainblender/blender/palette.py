"""Named colours shared across scenes (stdlib only, so Blender can import it).

Muted tones inspired by Figure 1 of Friedrich et al. (2026), "A precise atlas
of the human subcortex", bioRxiv, https://doi.org/10.64898/2026.02.13.705755
"""

# sRGB hex strings, in the order scenes cycle through them
COLORS: dict[str, str] = {
    "steel_blue": "#6F8FBF",
    "ochre": "#D98C2E",
    "dusty_rose": "#D4918C",
    "sage": "#5F8F7B",
    "brick_red": "#B5403E",
    "mauve": "#A6949E",
    "navy": "#3F4F85",
    "tan": "#C9A56A",
    "pale_blue": "#A9BDDB",
    "plum": "#8C6A8E",
}

PALETTE: tuple[str, ...] = tuple(COLORS.values())
