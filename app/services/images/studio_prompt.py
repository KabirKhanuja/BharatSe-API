"""The prompt that turns an artisan's phone photo into a catalogue image.

Adapted from a pipeline that already works in production on garments. Three
things in it are load bearing and should not be trimmed for brevity.

The "preserve exactly" list. Without it the model quietly improves the object:
a neater weave, a straighter rim, an invented motif. Delightful for art,
disqualifying for a craft catalogue where the buyer is paying for the actual
irregularity of a handmade thing.

The "no hands" paragraph. Artisans photograph their work while holding it, far
more often than not. Without an explicit instruction the model leaves fingers
in the frame.

The instruction to keep imperfection. This is the one genuinely new line for
this domain. A garment flatlay wants creases relaxed. A handmade pot does not
want its asymmetry corrected, because that asymmetry is the product.
"""

FLATLAY_PROMPT = """Turn this photograph of a single handmade object into a clean product image of
it, on a pure white background.

The object is: {label}

Produce:
- The object presented front facing and upright, as in a catalogue listing,
  filling most of the frame with a small even margin.
- A background of pure white, #FFFFFF, edge to edge. No gradient, no vignette,
  no floor line, no surface texture, no props.
- A soft contact shadow directly beneath the object where it would rest. Nothing
  more dramatic than that.

Remove entirely: hands, fingers, the table, cloth, floor, wall, packaging, price
tags, and any neighbouring object that appears in the frame.

Correct only the photography, never the object: neutralise the warm indoor
lighting so colours read as they would in daylight, straighten the camera angle,
and lift the exposure so detail in shadow is visible.

Preserve exactly, without stylising:
- The true colour in daylight terms.
- The pattern, its scale, and exactly where it sits on the object.
- The material and its texture: the weave, the grain, the glaze, the hammer
  marks, the thread.
- Every construction detail visible in the photo: joins, seams, stitching,
  handles, spouts, clasps, edges, the finish of the rim or hem.

This object was made by hand, and its irregularities are the product rather than
faults in it. Do not straighten a hand thrown curve, do not even out a hand
woven line, do not regularise a hand painted motif, and do not sharpen an
intentionally rough finish. Reproduce what is there.

Do not invent a print, a motif, a logo, a maker's mark, or any detail you cannot
see. Where a region is genuinely ambiguous, resolve it as plain material in the
object's main colour. Where part of the object is hidden, reconstruct only what
is unambiguous from symmetry.

Output the image only.

The object alone. If the photo shows it being held or worn, remove the person
entirely: no hands, no fingers, no skin, no clothing, no body. Reproduce the
object as if it had been set down and photographed on its own. A returned image
that still contains a person is a failed generation, not a stylistic choice."""


def render(label: str) -> str:
    """Fill the prompt for one object."""
    return FLATLAY_PROMPT.format(label=label or "a handmade craft object")
